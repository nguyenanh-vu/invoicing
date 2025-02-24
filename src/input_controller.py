import configparser
import os
import logging

from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

import invoicing.orders as orders
import invoicing.workspace as workspace


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
DEFAULT_TOKEN_NAME = "token.json"
DEFAULT_CREDENTIALS_NAME = "key.json"
SHEET_NAME_SEP = "@"


LOGGER = logging.getLogger(__name__)


class Input_Item:

    def __init__(self, index: int, name: str, price: float):
        self.index = index
        self.name = name
        self.price = price

    def __repr__(self):
        return "{}:{}:{}".format(self.index, self.name, self.price)


class Input_Controller:

    def __init__(self, input: str,
                 config: configparser.SectionProxy,
                 ws: workspace.Workspace,
                 required_args: List[str]):
        self.input = input
        self.config = config
        self.ws = ws
        self.required_args = required_args
        self.check_config()

    def read(self) -> List[orders.Order]:
        raise NotImplementedError

    @staticmethod
    def get_config_title() -> str:
        raise NotImplementedError

    def check_config(self) -> None:

        for arg in self.required_args:
            if arg not in self.config or not self.config.get(arg, None):
                raise KeyError("config missing key " + arg)
            else:
                LOGGER.debug("argument %s = %s", arg, self.config.get(arg))


class GoogleSheetsInput(Input_Controller):

    def __init__(self, input: str, config: configparser.SectionProxy, ws: workspace.Workspace):
        super().__init__(input, config, ws, [
            "cell.date",
            "cell.promotion.name",
            "cell.promotion.value",
            "column.order_id",
            "column.client",
            "column.delivery_point",
            "column.consignes",
            "column.sales",
            "column.last",
            "line.names",
            "line.price",
            "line.orders",
            "line.last"
        ])
        creds: Credentials
        try:
            creds = self.get_credentials()
        except Exception as e:
            LOGGER.error("error checking credentials")
            raise e
        self.creds: Credentials = creds
        input_split: List[str] = self.input.split(SHEET_NAME_SEP)
        self.sheet: str = ""
        if len(input_split) >= 1:
            self.input = input_split[0]

        if len(input_split) >= 2:
            self.sheet = input_split[1]

    def read(self) -> List[orders.Order]:

        try:
            self.check_config()
        except Exception as e:
            LOGGER.error("error input checking configuration%s", GoogleSheetsInput.get_config_title())
            raise e
        LOGGER.debug("successfully checked config %s", GoogleSheetsInput.get_config_title())

        LOGGER.debug("requesting date cell")
        date = self.get_cell(self.config["cell.date"])
        LOGGER.debug("order date: %s", date)

        LOGGER.debug("requesting promotion cells")
        promotion_name = self.get_cell(self.config["cell.promotion.name"])
        promotion_value = self.get_cell(self.config["cell.promotion.value"])

        promotion: Optional[orders.Promotion] = None
        if promotion_name and promotion_value:
            try:
                promotion = orders.Promotion(promotion_name, int(promotion_value))
                LOGGER.info("order promotion %s", promotion.__str__())
            except:
                pass

        items, consigns = self.read_items()
        LOGGER.info("found %d items, %d consigns", len(items), len(consigns))
        LOGGER.debug("items:")
        for i in items:
            LOGGER.debug(i)
        LOGGER.debug("consigns:")
        for i in consigns:
            LOGGER.debug(i)

        orders_table = self.request("A{}:{}{}".format(
            self.config.get("line.orders"),
            self.config.get("column.last"),
            self.config.get("line.last")
            ))

        res: List[orders.Order] = []

        for line in orders_table:

            order_id_column = GoogleSheetsInput.get_column_from_letter(self.config["column.order_id"])
            client_column = GoogleSheetsInput.get_column_from_letter(self.config["column.client"])
            delivery_point_column = GoogleSheetsInput.get_column_from_letter(self.config["column.delivery_point"])

            if order_id_column < len(line) and client_column < len(line):
                order_id = line[order_id_column]
                client = line[client_column]
                if order_id and client:

                    LOGGER.debug("filling order %s", order_id)
                    order: orders.Order = orders.Order()
                    order.promotion = promotion
                    order.order_id = order_id
                    order.client = client
                    order.date = date
                    if delivery_point_column < len(line):
                        order.delivery_point = line[delivery_point_column]
                    for i in items:
                        if i.index < len(line) and line[i.index]:
                            try:
                                qty = float(line[i.index])
                                item = orders.Item(i.name, qty, i.price)
                                order.items.append(item)
                            except:
                                pass
                    for i in consigns:
                        if i.index < len(line) and line[i.index]:
                            try:
                                qty = float(line[i.index])
                                item = orders.Item(i.name, qty, i.price)
                                order.consigns.append(item)
                            except:
                                pass
                    LOGGER.debug("Order %s: %s: %s: %s, %d items, %d consignes, %d total",
                                 order_id, client, date, promotion.__str__(),
                                 len(order.items), len(order.consigns), order.get_total_all())
                    res.append(order)
        LOGGER.info("found %d orders", len(res))
        return res

    @staticmethod
    def get_config_title() -> str:
        return "input.google"

    def get_credentials(self) -> Credentials:

        credential_path = self.config.get("path.credentials", os.path.join(self.ws.key, DEFAULT_CREDENTIALS_NAME))
        token_path = self.config.get("path.token", os.path.join(self.ws.key, DEFAULT_TOKEN_NAME))
        LOGGER.debug("credential_path: %s", credential_path)
        LOGGER.debug("token_path: %s", token_path)
        if not os.path.exists(credential_path):
            raise FileNotFoundError("Google OAuth2 token {} not found".format(credential_path))

        creds: Credentials
        found: bool = False
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            found = True
            LOGGER.debug("found connection token")
        # If there are no (valid) credentials available, let the user log in.
        if not found or not creds or not creds.valid:
            if found and creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                LOGGER.info("refreshed connection token")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credential_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
        return creds

    @staticmethod
    def get_column_from_letter(letter: str) -> int:
        return ord(letter.upper()[0]) - ord('A')

    def request(self, range: str) -> Any:

        LOGGER.debug("requesting range: %s", range)
        try:
            service = build("sheets", "v4", credentials=self.creds, cache_discovery=False)
            # Call the Sheets API
            sheet = service.spreadsheets()

            result = (
                sheet.values()
                .get(spreadsheetId=self.input, range=self.get_range(range))
                .execute()
            )
        except HttpError as e:
            LOGGER.error("error getting data:")
            raise e

        values = result.get("values", [])
        LOGGER.debug("got result, size %d", len(values))
        return values

    def get_cell(self, range: str) -> Optional[str]:
        res = self.request(range)
        if len(res) > 0 and len(res[0]) > 0:
            return res[0][0]
        else:
            return None

    def get_range(self, range: str) -> str:
        if not self.sheet:
            return range
        else:
            return self.sheet + "!" + range

    def read_items(self) -> tuple[List[Input_Item], List[Input_Item]]:

        items = []
        consigns = []

        price_line = self.config.getint("line.price")
        names_line = self.config.getint("line.names")
        last_column = self.config["column.last"]
        consigns_column = self.config["column.consignes"]
        sales_column = self.config["column.sales"]

        prices: List[str] = self.request("A{}:{}{}".format(price_line, last_column, price_line))[0]
        names: List[str] = self.request("A{}:{}{}".format(names_line, last_column, names_line))[0]

        for i in range(GoogleSheetsInput.get_column_from_letter(consigns_column), GoogleSheetsInput.get_column_from_letter(last_column)):
            if i < len(prices) and i < len(names):
                if names[i] and prices[i]:
                    try:
                        price = float(prices[i])
                        item = Input_Item(i, names[i].replace("\n", ""), price)
                        if i < GoogleSheetsInput.get_column_from_letter(sales_column):
                            consigns.append(item)
                        else:
                            items.append(item)
                    except:
                        pass

        return items, consigns


ALL = [
    GoogleSheetsInput
]


def get_input_controller(input: str, config: configparser.ConfigParser, ws: workspace.Workspace) -> Optional[Input_Controller]:
    for controller in ALL:
        if config.has_section(controller.get_config_title()):
            LOGGER.info("using input controller %s", controller.__name__)
            return controller(input, config[controller.get_config_title()], ws)
    return None
