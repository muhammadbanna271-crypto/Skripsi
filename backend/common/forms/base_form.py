from django import forms


class BootstrapModelForm(forms.ModelForm):
    """
    Base Form untuk seluruh project VillageInsight DSS.
    Semua widget otomatis memakai Bootstrap.
    """

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            widget = field.widget

            css = widget.attrs.get("class", "")

            # ==========================
            # Checkbox
            # ==========================
            if isinstance(widget, forms.CheckboxInput):

                widget.attrs["class"] = (
                    css + " form-check-input"
                ).strip()

            # ==========================
            # Dropdown
            # ==========================
            elif isinstance(widget, forms.Select):

                widget.attrs["class"] = (
                    css + " form-select"
                ).strip()

            # ==========================
            # Textarea
            # ==========================
            elif isinstance(widget, forms.Textarea):

                widget.attrs["class"] = (
                    css + " form-control"
                ).strip()

                widget.attrs.setdefault("rows", 4)

            # ==========================
            # Date
            # ==========================
            elif isinstance(widget, forms.DateInput):

                widget.attrs.update(
                    {
                        "class": "form-control",
                        "type": "date",
                    }
                )

            # ==========================
            # Email
            # ==========================
            elif isinstance(widget, forms.EmailInput):

                widget.attrs["class"] = (
                    css + " form-control"
                ).strip()

                widget.attrs.setdefault(
                    "placeholder",
                    "example@email.com",
                )

            # ==========================
            # Number
            # ==========================
            elif isinstance(widget, forms.NumberInput):

                widget.attrs["class"] = (
                    css + " form-control"
                ).strip()

            # ==========================
            # File Upload
            # ==========================
            elif isinstance(widget, forms.FileInput):

                widget.attrs["class"] = (
                    css + " form-control"
                ).strip()

            # ==========================
            # Default
            # ==========================
            else:

                widget.attrs["class"] = (
                    css + " form-control"
                ).strip()

            # Placeholder otomatis
            if (
                "placeholder" not in widget.attrs
                and field.label
                and not isinstance(widget, forms.CheckboxInput)
                and not isinstance(widget, forms.Select)
            ):

                widget.attrs["placeholder"] = (
                    f"Enter {field.label}"
                )