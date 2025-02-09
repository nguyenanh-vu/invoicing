import configparser
import os
import subprocess
from typing import List, Optional

import constants
import orders
import workspace


__all__ = [
    "Output_Controller"
    "PDFViaTex"
]

DEFAULT_LATEX_MODEL_PATH = "invoice.tex.template"
DEFAULT_LATEX_ITEM_LINE_MODEL = "<<NAME>>&<<QTY>>&<<PRICE>>&<<AMOUNT>>\\\\"

class Output_Controller:

    def __init__(self, config : Optional[configparser.SectionProxy], ws : workspace.Workspace):
        self.config = config
        self.ws = ws

    def save(self, order : orders.Order, name : str, folder: str) -> None:
        raise NotImplementedError

    def get_config_title() -> str:
        raise NotImplementedError


class PDFViaTex(Output_Controller):

    def __init__(self, config : Optional[configparser.SectionProxy], ws : workspace.Workspace):
        super().__init__(config, ws)

    def save(self, order : orders.Order, name : str, folder: str) -> None:

        if os.path.exists(folder):
            if not os.path.isdir(folder):
                raise NotADirectoryError("output folder {} already exists and is not a folder".format(folder))
        else:
            os.makedirs(folder, exist_ok=True)

        if self.config is not None:
            model = self.get_default_model( self.config.get("model.path", DEFAULT_LATEX_MODEL_PATH) )
            line_model = self.config.get("model.line", DEFAULT_LATEX_ITEM_LINE_MODEL)
        else: 
            model = self.get_default_model( DEFAULT_LATEX_MODEL_PATH )
            line_model = DEFAULT_LATEX_ITEM_LINE_MODEL

        infile = os.path.join(folder, name + '.tex')
        logfile = os.path.join(folder, name + '.log')
        auxfile = os.path.join(folder, name + '.aux')
        outfile = os.path.join(folder, name + '.out')

        data = ""

        if not os.path.exists(model):
            raise FileNotFoundError("model file {} not found".format(model))
        if os.path.exists(infile):
            raise FileExistsError("output file {} already exists".format(infile))
        if os.path.exists(outfile):
            raise FileExistsError("output file {} already exists".format(outfile))

        with open(model, 'r') as f:
            data = f.read()

        data = data.replace("<<MODEL_FOLDER>>", os.path.dirname(os.path.abspath(model)).replace("\\", "/") )
        data = data.replace("<<CLIENT>>", order.client)
        data = data.replace("<<DELIVERY_POINT>>", order.delivery_point)
        data = data.replace("<<DATE>>", order.date)
        data = data.replace("<<ORDER_ID>>", order.order_id)
        data = data.replace("<<PROMOTION>>", self.get_promotion_line(order, line_model))
        data = data.replace("<<TOTAL_SALES>>", str(order.get_total_price()))
        data = data.replace("<<TO_PAY>>", str(order.get_to_pay()))
        data = data.replace("<<TOTAL_CONSIGNS>>", str(order.get_total_consigns()))
        data = data.replace("<<TOTAL>>", str(order.get_total_all()))
        data = data.replace("<<ITEMS>>", self.get_items_lines(order.items, line_model))
        data = data.replace("<<CONSIGNS>>", self.get_items_lines(order.consigns, line_model))

        with open(infile, 'w', encoding="utf-8") as f:
            f.write(data)

        cmd = ['pdflatex', '-interaction', 'nonstopmode', '-output-directory', folder, infile]
        proc = subprocess.Popen(cmd, stdout=open(os.devnull, 'wb'))
        proc.communicate()

        retcode = proc.returncode
        if not retcode == 0:
            os.unlink(auxfile)
            os.unlink(outfile)
            raise ValueError('Error {} executing command: {}'.format(retcode, ' '.join(cmd))) 

        try:
            os.unlink(logfile)
            os.unlink(auxfile)
            os.unlink(outfile)
            os.unlink(infile)
        except:
            return
        
    def get_items_lines(self, items : List[orders.Item], line_model : str) -> str:

        lines : List[str] = []
        for item in items:
            lines.append(
                line_model
                .replace("<<NAME>>", item.name)
                .replace("<<QTY>>", str(item.qty))
                .replace("<<PRICE>>", str(item.price))
                .replace("<<AMOUNT>>", str(item.amount))
            )
        return "\n".join(lines)

    def get_promotion_line(self, order : orders.Order, line_model : str) -> str:

        if order.promotion is None:
            return None
        else:
            return line_model.replace("<<NAME>>", order.promotion.name).replace("<<QTY>>", "").replace("<<PRICE>>", "").replace("<<AMOUNT>>", str(order.promotion.percent) + "\\%")

    def get_default_model(self, name : str) -> str:
        return os.path.join(self.ws.model, name)

    def get_config_title() -> str:
        return "output.latex"


ALL = [
    PDFViaTex
]


def get_output_controller(config : configparser.ConfigParser, ws : workspace.Workspace) -> List[Output_Controller]:
    res = []
    for controller in ALL:
        if config.has_section(controller.get_config_title()):
            res.append(controller(config[controller.get_config_title()], ws))
    return res
