from starlette_wtf import StarletteForm
from wtforms import Form, BooleanField, StringField, validators, DateTimeField


# Make a form for the library table
# Note: this could be easier -- we could automtically create a form from a sqlalchemy
# model, butthe bookserver owns the library model definition


class LibraryForm(StarletteForm):
    title = StringField("Title")
    subtitle = StringField("SubTitle")
    description = StringField("Description")
    authors = StringField("Authors")
    shelf_section = StringField(
        "Shelf Section",
        description="Look at the library page to see the existing list of sections.  Please try to use one of those.  Note do not add the Textbooks: to the end.",
    )
    basecourse = StringField("Base Course or Document ID")
    build_system = StringField("Build System")
    for_classes = BooleanField("Available for courses")
    is_visible = BooleanField("Visible to Everyone in Library")
    github_url = StringField("Github URL")
    main_page = StringField("Main page")
    # last_build = DateTimeField("Last Build")
