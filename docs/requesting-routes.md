# Requesting Routes

## Using the in-built demo utility

A demo script is available in this repo (`polarrouteserver/demo.py`) to be used as a utility for making route requests.

To obtain, either:

+ Clone this whole repo
+ Download the file from its GitHub page here: https://github.com/bas-amop/PolarRoute-server/blob/main/demo.py

This can be done with `wget` by running:

```
wget https://raw.githubusercontent.com/bas-amop/PolarRoute-server/refs/heads/main/polarrouteserver/demo.py
```

To run, you'll just need python ~3.11 installed. Earlier versions of python may work, but are untested.

### Usage
Help for the utility can be printed out by running `python demo.py --help`.

Alternatively, if you have the package installed, a command named `request_route` is made available.

```sh
$ request_route --help
# OR
$ python demo.py --help

usage: demo.py [-h] [-u URL] -s [START] -e [END] [-d [DELAY]] [-f] [-o [OUTPUT]]

Requests a route from polarRouteServer, repeating the request for status until the route is available. Specify start and end points by coordinates or from one of the standard locations: ['bird', 'falklands',
'halley', 'rothera', 'kep', 'signy', 'nyalesund', 'harwich', 'rosyth']

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Base URL to send request to.
  -s [START], --start [START]
                        Start location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01
  -e [END], --end [END]
                        End location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01
  -d [DELAY], --delay [DELAY]
                        (integer) number of seconds to delay between status calls.
  -f, --force           Force polarRouteServer to recalculate the route even if it is already available.
  -o [OUTPUT], --output [OUTPUT]
                        File path to write out route to. (Default: None and print to stdout)
```

So to request a route from Falklands to Rothera, for example:

```sh
python demo.py --url example-polar-route-server.com -s falklands -e rothera --delay 120 --output demo_output.json
```

This will request the route from the server running at `example-polar-route-server.com`, and initiate a route calculation if one is not already available.

The utility will then request the route's status every `120` seconds.

The HTTP response from each request will be printed to stdout.

Once the route is available it will be returned, or if 10 attempts to get the route have passed, the utility will stop.
