import configparser
from numbers import Number
import os
import logging

from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import invoicing.orders as orders
import invoicing.workspace as workspace


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
DEFAULT_TOKEN_NAME = "token.json"
DEFAULT_CREDENTIALS_NAME = "key.json"


LOGGER = logging.getLogger(__name__)


class Input_Item:

    def __init__(self, index : int, name : str, price : Number):
        self.index = index
        self.name = name
        self.price = price

    def __repr__(self):
        return "{}:{}:{}".format(self.index, self.name, self.price)


class Input_Controller:

    def __init__(self, input : str, config : Optional[configparser.SectionProxy], ws : workspace.Workspace):
        self.input = input
        self.config = config
        self.ws = ws

    def read(self, config : Optional[configparser.SectionProxy]) -> List[orders.Order]:
        raise NotImplementedError

    def get_config_title() -> str:
        raise NotImplementedError


class GoogleSheetsInput(Input_Controller):

    def __init__(self, input : str, config : Optional[configparser.SectionProxy], ws : workspace.Workspace):
        super().__init__(input, config, ws)

    def read(self) -> List[orders.Order]:

        try:
            self.check_config()
        except Exception as e:
            LOGGER.error("error input checking configuration%s", GoogleSheetsInput.get_config_title())
            raise e
        LOGGER.debug("successfully checked config %s", GoogleSheetsInput.get_config_title())

        creds : Credentials
        try:
            creds = self.get_credentials()
        except Exception as e:
            LOGGER.error("error checking credentials")
            raise e

        LOGGER.debug("requesting date cell")
        date = self.request(creds, self.config.get("cell.date"))[0][0]
        LOGGER.debug("order date: %s", date)

        LOGGER.debug("requesting promotion cells")
        promotion_name = self.request(creds, self.config.get("cell.promotion.name"))[0][0]
        promotion_value = self.request(creds, self.config.get("cell.promotion.value"))[0][0]

        promotion : orders.Promotion
        if promotion_name and promotion_value:
            try:
                promotion : orders.Promotion = orders.Promotion(promotion_name, int(promotion_value))
                LOGGER.info("order promotion %s", promotion.__str__())
            except:
                pass

        items, consigns = self.read_items(creds)
        LOGGER.info("found %d items, %d consigns", len(items), len(consigns))
        LOGGER.debug("items:")
        for i in items:
            LOGGER.debug(i)
        LOGGER.debug("consigns:")
        for i in consigns:
            LOGGER.debug(i)

        orders_table = self.request(creds, "A{}:{}{}".format(
            self.config.get("line.orders"),
            self.config.get("column.last"),
            self.config.get("line.last")
            ))

        res : List[orders.Order] = []

        for line in orders_table:

            order_id_column = GoogleSheetsInput.get_column_from_letter(self.config.get("column.order_id"))
            client_column = GoogleSheetsInput.get_column_from_letter(self.config.get("column.client"))
            delivery_point_column = GoogleSheetsInput.get_column_from_letter(self.config.get("column.delivery_point"))

            if order_id_column < len(line) and client_column < len(line):
                order_id = line[order_id_column]
                client = line[client_column]
                if order_id and client:

                    LOGGER.debug("filling order %s", order_id)
                    order : orders.Order = orders.Order()
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

    def get_config_title() -> str:
        return "input.google"

    def check_config(self) -> None:

        if self.config is None:
            raise ValueError("No input configuration")

        args = [
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
        ]

        for arg in args:
            if arg not in self.config or not self.config.get(arg, None):
                raise KeyError("config missing key " + arg)
            else:
                LOGGER.debug("argument %s = %s", arg, self.config.get(arg))

    def get_credentials(self) -> Credentials:
        
        credential_path = self.config.get("path.credentials", os.path.join(self.ws.key, DEFAULT_CREDENTIALS_NAME))
        token_path = self.config.get("path.token", os.path.join(self.ws.key, DEFAULT_TOKEN_NAME))
        LOGGER.debug("credential_path: %s", credential_path)
        LOGGER.debug("token_path: %s", token_path)
        if not os.path.exists(credential_path):
            raise FileNotFoundError("Google OAuth2 token {} not found".format(credential_path))

        creds : Credentials = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            LOGGER.debug("found connection token")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
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

    def get_column_from_letter(letter : str) -> int:
        return ord( letter.upper()[0] ) - ord('A')

    def request(self, creds : Credentials, range : str) -> Any:

        LOGGER.debug("requesting range : %s", range)
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        # Call the Sheets API
        sheet = service.spreadsheets()

        result = (
            sheet.values()
            .get(spreadsheetId=self.input, range=range)
            .execute()
        )

        values = result.get("values", [])
        LOGGER.debug("got result, size %d", len(values))
        return values

    def read_items(self, creds : Credentials) -> tuple[List[Input_Item],List[Input_Item]]:

        items = []
        consigns = []

        price_line = self.config.getint("line.price")
        names_line = self.config.getint("line.names")
        last_column = self.config.get("column.last")
        consigns_column = self.config.get("column.consignes")
        sales_column = self.config.get("column.sales")

        prices : List[str] = self.request(creds, "A{}:{}{}".format(price_line, last_column, price_line))[0]
        names : List[str] = self.request(creds, "A{}:{}{}".format(names_line, last_column, names_line))[0]
        
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


def get_input_controller(input : str, config : configparser.ConfigParser, ws : workspace.Workspace) -> Optional[Input_Controller]:
    for controller in ALL:
        if config.has_section(controller.get_config_title()):
            LOGGER.info("using input controller %s", controller.__name__)
            return controller(input, config[controller.get_config_title()], ws)
    return None
