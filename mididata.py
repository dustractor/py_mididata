import mido
import pathlib,argparse,os,sys
from itertools import cycle
import sqlite3
from urllib.parse import quote_plus
from xml.dom import minidom

home = pathlib.Path.home()
here = pathlib.Path(__file__).parent
# _TESTING = True
_TESTING = False
_DBFILE =  here / "midis.db"
_DEFAULTROOTDIR = home /"Documents"/"Image-Line"/"FL Studio"/"Presets"/"Scores" 
_DEFAULTOUTPUT = home / "Desktop" / "midi_data.html"
_TESTINGROOT = home / "Desktop" / "testmidis"

#{{{1 minidom setup

def _elem_inplace_addition(self,other):
    self.appendChild(other)
    return self
def _elem_textnode(self,text):
    textnode = self.ownerDocument.createTextNode(text)
    self.appendChild(textnode)
    return self
def _elem_set_attributes_from_tuple(self,*args):
    for k,v in args:
        self.setAttribute(k,str(v))
    return self

minidom.Element.__iadd__ = _elem_inplace_addition
minidom.Element.txt = _elem_textnode
minidom.Element.attrt = _elem_set_attributes_from_tuple
minidom.Element.__str__ = lambda s:s.toprettyxml().strip()

#}}}1

args = argparse.ArgumentParser()
if _TESTING:
    if _DBFILE.is_file():
        _DBFILE.unlink()
        print("removed database file")
    args.add_argument("--scan",default=True)
    args.add_argument("--rootdir",default=_TESTINGROOT)
else:
    args.add_argument("--scan",action="store_true")
    args.add_argument("--rootdir",default=_DEFAULTROOTDIR)

args.add_argument("--output",default=_DEFAULTOUTPUT)
ns = args.parse_args()

# {{{1 ddl

ddl = """
create table if not exists midis (
id integer primary key,
name text,
keys text,
notecount integer,
noteset text,
errors text,
unique (name) on conflict replace);
"""

# }}}1

cx = sqlite3.connect(_DBFILE)
cx.executescript(ddl)
cx.commit()


note_d = {a:b for (a,b) in zip(
    range(128),
    cycle(["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]))}

def analyze(f):
    info = dict(name=str(f))
    try:
        mid = mido.MidiFile(f)
    except OSError:
        info["error"] = str(sys.exc_info()[1])
        return info
    note_set = set()
    key_sigs = list()
    note_count = 0
    for track in mid.tracks:
        for message in track:
            if message.type == "key_signature":
                key_sigs.append(message.key)
            if message.type == "note_on":
                note_set.add(note_d[message.note])
                note_count += 1
    key_sigs = "_".join(list(set(key_sigs))) if len(key_sigs) else "NONE"
    info["keys"] = key_sigs
    info["noteset"] = sorted(note_set)
    info["notecount"] = note_count
    return info

def scan():
    fpath = None
    for r,ds,fs in os.walk(ns.rootdir):
        root = pathlib.Path(r)
        for f in fs:
            if f.endswith(".mid"):
                print("Scanning",fpath)
                fpath = root / f
                info = analyze(fpath)
                if "error" in info:
                    cx.execute("insert into midis (name,errors) values (?,?)",
                               (info["name"],info["error"]))
                else:
                    cx.execute("insert into midis (name,keys,notecount,noteset) values (?,?,?,?)",
                               (info["name"],str(info["keys"]),info["notecount"],str(info["noteset"])))
    cx.commit()

def distinct_keys():
    keys = list()
    for kt in cx.execute("select distinct keys from midis"):
        keys.append(kt[0])
    return keys

list(map(print,distinct_keys()))

def report():
    doc = minidom.Document()
    elem = doc.createElement
    root = elem("html")
    head = elem("head")
    root += head
    title = elem("title")
    head += title
    title.txt("midi data")
    body = elem("body")
    root += body

    nav = elem("nav")
    body += nav
    nav_ul = elem("ul")
    nav += nav_ul

    article = elem("article")
    body += article

    articles = dict()


    for k in distinct_keys():
        ul = elem("ul")
        key_href = "#" + k
        key_text = k.replace("_"," ")
        li = elem("li")
        nav_ul += li
        a = elem("a")
        li += a
        a.attrt(("href",key_href))
        a.txt(key_text)
        h3 =  elem("h3")
        article += h3
        h3.attrt(("id",k))
        h3.txt(k)
        article_ul = elem("ul")
        article += article_ul
        articles[k] = article_ul
    
    for name,errors,k,noteset,notecount in cx.execute(
            "select name,errors,keys,noteset,notecount from midis order by keys"):
        li = elem("li")
        articles[k] += li
        h3 = elem("h3")
        li += h3
        a = elem("a")
        h3 += a
        a.attrt(("href","http://127.0.0.1:5000/"+quote_plus(name)))
        a.txt(name)
        if errors:
            p = elem("p")
            li += p
            p.txt(errors)
            continue
        p = elem("p")
        li += p
        p.txt(k)
        p = elem("p")
        li += p
        p.txt(noteset)
        p = elem("p")
        li += p
        p.txt(str(notecount))
    with open(ns.output,"w",encoding="UTF8") as f:
        f.write(str(root))

def main():
    if ns.scan:
        scan()
    report()
if __name__ == "__main__":
    main()
