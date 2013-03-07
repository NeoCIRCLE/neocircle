from cloud.settings import DEBUG

def process_debug(req):
    return {'DEBUG': DEBUG}
