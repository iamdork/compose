from __future__ import absolute_import
from __future__ import unicode_literals

import compose.config.config
import compose.cli.command
from compose.config.config import load
import compose.cli.main

import dork.environment
import dork.command
import dork.config
import dork.proxy
import dork.snapshot


# Initialize dork environment variables.
dork.environment.initialize()

# Ensure the proxy container is running.
dork.proxy.initialize()

# Tell snapshot manager to start service containers.
dork.snapshot.initialize()

# Replace compose TopLevelCommand with custom derivation.
compose.cli.main.TopLevelCommand = dork.command.DorkTopLevelCommand


def __inject(config):
    return dork.config.preprocess(load(config))

# Inject config preprocessing into docker-compose
compose.config.config.load = __inject
compose.cli.command.config.load = __inject

# Run docker-compose main function.
compose.cli.main.main()
