"""Pydantic request / response schemas, grouped by resource.

Conventions (see ``docs/architecture/04-api-design.md`` §2.4):

* Request schemas:  ``<Resource>CreateRequest``, ``<Resource>UpdateRequest``
* Response schemas: ``<Resource>Response``, ``<Resource>ListResponse``
* Every response model sets ``model_config = ConfigDict(from_attributes=True)``
  via :class:`backend.api.schemas.common.ORMModel`.
* Envelope is applied at the route boundary using
  :func:`backend.api.schemas.common.envelope`.
"""

from __future__ import annotations
