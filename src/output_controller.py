import configparser
import os
import subprocess
import logging
from typing import List

import invoicing.orders as orders
import invoicing.workspace as workspace
import invoicing.tokens as tokens
import invoicing.constants as constants


LOGGER = logging.getLogger(__name__)
DEFAULT_LATEX_MODEL_PATH = "invoice.tex.template"
DEFAULT_LATEX_ITEM_LINE_MODEL = "&".join([
    tokens.NAME.get_label(),
    tokens.QTY.get_label(),
    tokens.PRICE.get_label(),
    tokens.AMOUNT.get_label()
]) + "\\\\"


class Output_Controller:

    def __init__(self, config: configparser.SectionProxy, ws: workspace.Workspace):
        self.config = config
        self.ws = ws

    def save(self, order: orders.Order, name: str, folder: str) -> None:
        raise NotImplementedError

    @staticmethod
    def get_config_title() -> str:
        raise NotImplementedError

    def get_items_lines(self, items: List[orders.Item], line_model: str) -> str:

        lines: List[str] = []
        for item in items:
            data = line_model
            data = tokens.NAME.replace_item(data, item)
            data = tokens.QTY.replace_item(data, item)
            data = tokens.PRICE.replace_item(data, item)
            data = tokens.AMOUNT.replace_item(data, item)
            lines.append(data)
        return "\n".join(lines)

    def get_promotion_line(self, order: orders.Order, line_model: str) -> str:

        if order.promotion is None:
            return ""
        else:
            line = line_model
            line = tokens.NAME.replace(line, order.promotion.name)
            line = tokens.QTY.replace(line, "")
            line = tokens.PRICE.replace(line, "")
            line = tokens.AMOUNT.replace(line, str(order.promotion.percent) + "\\%")
            return line

    def get_filename(self, name: str, order: orders.Order) -> str:
        if "format.path" in self.config and self.config["format.path"]:
            filename = self.config["format.path"]
            filename = tokens.ORDER_DATE.replace_order(filename, order)
            filename = tokens.NAME.replace(filename, name)
            filename = tokens.ORDER_ID.replace_order(filename, order)
            filename = tokens.TODAY.replace_data(filename, self.config.get("format.datetime", constants.DEFAULT_DATETIME_FORMAT))
            filename = tokens.TIME.replace_data(filename, self.config.get("format.time", constants.DEFAULT_TIME_FORMAT))
            filename = tokens.DATE.replace_data(filename, self.config.get("format.date", constants.DEFAULT_DATE_FORMAT))
            return filename
        else:
            return name

    def get_folder(self, folder: str, order: orders.Order) -> str:
        if "format.folder.output" in self.config and self.config["format.folder.output"]:
            filename = self.config["format.folder.output"]
            filename = tokens.ORDER_DATE.replace_order(filename, order)
            filename = tokens.ORDER_ID.replace_order(filename, order)
            filename = tokens.TODAY.replace_data(filename, self.config.get("format.datetime", constants.DEFAULT_DATETIME_FORMAT))
            filename = tokens.TIME.replace_data(filename, self.config.get("format.time", constants.DEFAULT_TIME_FORMAT))
            filename = tokens.DATE.replace_data(filename, self.config.get("format.date", constants.DEFAULT_DATE_FORMAT))
            return os.path.join(folder, filename)
        else:
            return folder


class PDFViaTex(Output_Controller):

    def __init__(self, config: configparser.SectionProxy, ws: workspace.Workspace):
        super().__init__(config, ws)

    def save(self, order: orders.Order, name: str, folder: str) -> None:

        LOGGER.info("generating PDF with LaTex for order %s", order.order_id)
        folder_path = self.get_folder(folder, order)
        LOGGER.info("output folder: %s", folder_path)
        if os.path.exists(folder_path):
            if not os.path.isdir(folder_path):
                raise NotADirectoryError("output folder {} already exists and is not a folder".format(folder_path))
        else:
            os.makedirs(folder_path, exist_ok=True)

        model = self.config.get("model.path", self.get_default_model())
        line_model = self.config.get("model.line", DEFAULT_LATEX_ITEM_LINE_MODEL)

        LOGGER.debug("path to model %s", model)
        LOGGER.debug("line model: %s", line_model)

        filename = self.get_filename(name, order)
        infile = os.path.join(folder_path, filename + '.tex')
        logfile = os.path.join(folder_path, filename + '.log')
        auxfile = os.path.join(folder_path, filename + '.aux')
        outfile = os.path.join(folder_path, filename + '.out')
        LOGGER.info("output file: %s", outfile)

        data = ""

        if not os.path.exists(model):
            raise FileNotFoundError("model file {} not found".format(model))
        if os.path.exists(infile):
            raise FileExistsError("output file {} already exists".format(infile))
        if os.path.exists(outfile):
            raise FileExistsError("output file {} already exists".format(outfile))

        with open(model, 'r') as f:
            data = f.read()

        data = tokens.MODEL_FOLDER.replace(data=data,
                                           content=os.path.dirname(os.path.abspath(model)).replace("\\", "/"))
        data = tokens.CLIENT.replace_order(data, order)
        data = tokens.DELIVERY_POINT.replace_order(data, order)
        data = tokens.ORDER_DATE.replace_order(data, order)
        data = tokens.ORDER_ID.replace_order(data, order)
        data = tokens.PROMOTION.replace(data=data, content=self.get_promotion_line(order, line_model))
        data = tokens.TOTAL_SALES.replace_order(data, order)
        data = tokens.TO_PAY.replace_order(data, order)
        data = tokens.TOTAL_CONSIGNS.replace_order(data, order)
        data = tokens.TOTAL.replace_order(data, order)
        data = tokens.ITEMS.replace(data=data, content=self.get_items_lines(order.items, line_model))
        data = tokens.CONSIGNS.replace(data=data, content=self.get_items_lines(order.consigns, line_model))

        with open(infile, 'w', encoding="utf-8") as f:
            f.write(data)

        LOGGER.info("LaTex file created in %s", infile)
        cmd = ['pdflatex', '-interaction', 'nonstopmode', '-output-directory', folder_path, infile]
        proc = subprocess.Popen(cmd, stdout=open(os.devnull, 'wb'))
        proc.communicate()

        retcode = proc.returncode
        if not retcode == 0:
            try:
                os.unlink(auxfile)
                os.unlink(outfile)
            except:
                pass
            LOGGER.error("Error generating pdf, check %s for more information", logfile)
            raise ValueError('Error {} executing command: {}'.format(retcode, ' '.join(cmd)))

        try:
            os.unlink(logfile)
            os.unlink(auxfile)
            os.unlink(outfile)
            os.unlink(infile)
        except:
            pass
        LOGGER.info("successfully generated PDF with LaTex for order %s", order.order_id)

    def get_default_model(self) -> str:
        return os.path.join(self.ws.model, DEFAULT_LATEX_MODEL_PATH)

    @staticmethod
    def get_config_title() -> str:
        return "output.latex"


ALL = [
    PDFViaTex
]


def get_output_controller(config: configparser.ConfigParser, ws: workspace.Workspace) -> List[Output_Controller]:
    res: List[Output_Controller] = []
    for controller in ALL:
        if config.has_section(controller.get_config_title()):
            LOGGER.info("using output controller %s", controller.__name__)
            res.append(controller(config[controller.get_config_title()], ws))
    return res
