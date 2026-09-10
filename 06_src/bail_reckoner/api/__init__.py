"""Layer M7's API — the REST contract over the structured Report and Application objects.

Built before any UI, on Abhishek's direction (D-076): the objects are already
renderer-agnostic, and the API is the contract a frontend consumes. The engine (Layer C)
imports nothing from here; this package imports the engine, never the reverse, so D-050's
purity stays visible in the dependency graph.

Two hard properties every response upholds:

* **Honesty about the data behind it (D-076, executing the zero-rows directive).** Every
  response envelope names the resolution mode and the verified-row count, and while zero
  verified rows exist every computed output carries an unmissable warning that it was
  computed from synthetic fixtures or resolved nothing. An API that looks operational while
  computing nothing is worse than no API.
* **D-060 holds at the boundary.** The API accepts no user-supplied maximum. Offences arrive
  as (regime, section, variant) and are resolved server-side against the verified repository
  (or the loudly-labelled synthetic fixtures); an unresolved offence abstains via
  OFFENCE_NOT_IN_DATABASE exactly as the engine always has.
"""

from bail_reckoner.api.app import create_app

__all__ = ["create_app"]
