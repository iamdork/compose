from compose.cli.main import TopLevelCommand
import dork.snapshot


class DorkTopLevelCommand(TopLevelCommand):
    __doc__ = TopLevelCommand.__doc__ + \
              "  snapshot           Save or restore runtime data snapshots."

    def snapshot(self, options):
        """
        Save or restore volume snapshots.
        Usage: snapshot COMMAND [SNAPSHOT...]

        Commands:
          save   Store volumes state as snapshot.
          load   Load the closest snapshot or a specific one.
          ls     List all available snapshots.
          rm     Clean up snapshots or remove a specific one.
        """
        if options['COMMAND'] == 'save':
            dork.snapshot.save(options['SNAPSHOT'][0] if options['SNAPSHOT'] else None)
        if options['COMMAND'] == 'load':
            dork.snapshot.load(options['SNAPSHOT'][0] if options['SNAPSHOT'] else None)
        if options['COMMAND'] == 'rm':
            dork.snapshot.rm(options['SNAPSHOT'])
        if options['COMMAND'] == 'ls':
            dork.snapshot.ls()
