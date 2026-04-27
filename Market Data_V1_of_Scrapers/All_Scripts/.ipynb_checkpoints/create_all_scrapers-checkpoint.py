import json
from pathlib import Path

S = Path.home() / 'Job_Scrapers' / 'All_Scripts'
K = {"display_name":"Python [conda env:JobAnalyser]","language":"python","name":"conda-env-JobAnalyser-py"}

def nb(cells):
    return {"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":K,"language_info":{"name":"python","version":"3.10.0"}},"cells":cells}
def c(src):
    return {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":src}
def m(src):
    return {"cell_type":"markdown","metadata":{},"source":src}

