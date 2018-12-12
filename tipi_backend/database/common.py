import hashlib


def generateId(*args):
    try:
        return hashlib.sha1(
                u''.join(args).encode('utf-8')
                ).hexdigest()
    except:
        return 'ID_ERROR'

