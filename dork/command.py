import compose.cli.main
import dork.snapshot


class DorkTopLevelCommand(compose.cli.main.TopLevelCommand):
    __doc__ = compose.cli.main.TopLevelCommand.__doc__ + \
              "  dork               Save or restore runtime data snapshots."

    def dork(self, options):
        """
        Save or restore volume snapshots.
        Usage: dork COMMAND [SNAPSHOT]

        Commands:
          save   Store current state as snapshot.
          load   Load a specific snapshot.
          list   List all available snapshots.
          clear  Reset runtime data.
        """
        if options['COMMAND'] == 'save':
            dork.snapshot.save(options['SNAPSHOT'])
        if options['COMMAND'] == 'load':
            dork.snapshot.load(options['SNAPSHOT'])
        if options['COMMAND'] == 'clear':
            dork.snapshot.clear()
        if options['COMMAND'] == 'ls':
            dork.snapshot.ls()
