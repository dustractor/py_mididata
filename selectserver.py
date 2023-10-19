import flask
from urllib.parse import unquote_plus
import subprocess
import pathlib
app = flask.Flask(__name__)

@app.route("/<f_url>",methods={"GET"})
def index(f_url):
    print("unquote_plus(f_url):",unquote_plus(f_url))
    fpath = unquote_plus(f_url)
    subprocess.run("explorer /select,\"{}\"".format(fpath),shell=True)
    
    return "OK",200

