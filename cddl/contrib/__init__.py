"""Space for your own, private extractors.

Put site-specific :class:`~cddl.extractors.base.Extractor` subclasses here (or in
any importable package) and hand them to the pipeline::

    from cddl import Options, download
    from cddl.contrib.my_site import MySiteExtractor

    download(url, Options(out_dir="library"), extra_extractors=[MySiteExtractor])

Nothing in this package is shipped by the project: it exists so that code you are
authorised to run stays outside the shared engine.
"""