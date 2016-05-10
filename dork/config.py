import dork.snapshot
import dork.proxy


def preprocess(config):
    return dork.proxy.process_config(dork.snapshot.process_config(config))
