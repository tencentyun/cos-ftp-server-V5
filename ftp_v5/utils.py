# -*- coding:utf-8 -*-

import datetime

def reformat_lm(last_modified, form="object"):
    if last_modified is None:
        dt_modified = datetime.datetime(1970, 1, 1)
    else:
        try:
            #this is the format used when you use get_all_keys()
            dt_modified = datetime.datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            #this is the format used when you use get_key()
            dt_modified = datetime.datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
        except:
            raise

    if form == "object":
        return dt_modified
    elif form == "ls":
        if (datetime.datetime.now() - dt_modified).days < 180:
            return dt_modified.strftime("%b %d %H:%M")
        else:
            return dt_modified.strftime("%b %d %Y")
    else:
        return dt_modified.strftime("%Y%m%d%H%M%S")
