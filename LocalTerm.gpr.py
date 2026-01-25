from gramps.gui import plug
from gramps.version import major_version, VERSION_TUPLE

if VERSION_TUPLE < (5, 2, 0):
    additional_args = {
#        "status": UNSTABLE,
    }
else:
    additional_args = {
        "audience": EXPERT,
        "status": EXPERIMENTAL, #reduce the "LOG.setLevel()" setting for "STABLE"
#        "maintainers": "Kaj Mikkelsen",
#        "maintainers_email": "",
    }


register(
    GRAMPLET,
    id="LocalTerm Gramplet",
    name=_("Localized Gramps Glossary Terminology"),
    description=_("Localized index to Gramps Glossary terminology"),
    authors=["Kaj Mikkelsen"],
    authors_email=["kmi@vgdata.dk"],
    version = '0.3.4',
    fname="LocalTerm.py",
    height=20,
    detached_width=510,
    detached_height=480,
    expand=True,
    gramplet="LocalTerm",
    gramplet_title=_("Localized Glossary Index"),
    gramps_target_version=major_version,
    help_url="https://github.com/kajmikkelsen/LocalTerm",
#    help_url="Addon:LocalTerm",
    navtypes=["Person", "Dashboard", "Note"],
    include_in_listing=True,
    **additional_args,
)
