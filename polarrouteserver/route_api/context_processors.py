import os


def export_vars(request):
    data = {}
    data["FRONTEND"] = os.environ["POLARROUTE_FRONTEND"]
    return data
