class Checkbot:
    def __init__(self):
        pass


def exception_handler(*args, **kwargs):
    # prevents invocation retry
    return True


if __name__ == '__main__':
    Checkbot().check()
