from main import *
from config import *


if __name__ == "__main__":
    app.run(
        host = SERVER_HOST,
        port = SERVER_PORT,
        debug = DEBUG_MODE
    )