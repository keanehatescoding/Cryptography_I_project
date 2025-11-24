import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

# Constants
USERNAME_REGEX = r"^[a-zA-Z0-9_]+$"
USERNAME_MESSAGE = "Only letters, numbers, and underscores allowed."


# Custom Validators
class PasswordStrength:
    """
    Validator that checks password strength and provides specific error messages.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        password = field.data
        errors = []

        if len(password) < 8:
            errors.append("at least 8 characters")
        if len(password) > 64:
            errors.append("no more than 64 characters")
        if not re.search(r"[a-z]", password):
            errors.append("at least one lowercase letter")
        if not re.search(r"[A-Z]", password):
            errors.append("at least one uppercase letter")
        if not re.search(r"\d", password):
            errors.append("at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('at least one special character (!@#$%^&*(),.?":{}|<>)')

        if errors:
            error_message = "Password must contain " + ", ".join(errors) + "."
            raise ValidationError(error_message)


def username_validator():
    """Returns a list of validators for username fields."""
    return [
        DataRequired(message="Username is required."),
        Length(min=3, max=50, message="Username must be between 3 and 50 characters."),
        Regexp(USERNAME_REGEX, message=USERNAME_MESSAGE),
    ]


def password_validator(confirm_field=None):
    """Returns a list of validators for password fields."""
    validators = [
        DataRequired(message="Password is required."),
        Length(min=8, max=64, message="Password must be between 8 and 64 characters."),
        PasswordStrength(),
    ]
    if confirm_field:
        validators.insert(1, EqualTo(confirm_field, message="Passwords do not match."))
    return validators


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "e.g. john_doe123", "autocomplete": "username"},
    )
    password = PasswordField(
        "Password",
        validators=password_validator(confirm_field="confirm"),
        render_kw={"autocomplete": "new-password"},
        description="Must contain uppercase, lowercase, digit, and special character (8-64 chars)",
    )
    confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(message="Please confirm your password.")],
        render_kw={"autocomplete": "new-password"},
    )
    public_key = FileField(
        "Public Key (PEM format)",
        validators=[
            FileRequired(message="Public key file is required."),
            FileAllowed(["pem", "key"], "Only .pem or .key files allowed."),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "Username", "autocomplete": "username"},
    )
    password = PasswordField(
        "Password",
        validators=password_validator(),
        render_kw={"autocomplete": "current-password"},
    )
    submit = SubmitField("Log In")


class UpdatePasswordForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "e.g. john_doe123", "autocomplete": "username"},
    )
    oldpass = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required.")],
        render_kw={"autocomplete": "current-password"},
    )
    password = PasswordField(
        "New Password",
        validators=password_validator(confirm_field="confirm"),
        render_kw={"autocomplete": "new-password"},
        description="Must contain uppercase, lowercase, digit, and special character (8-64 chars)",
    )
    confirm = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(message="Please confirm your new password.")],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Update Password")

    def validate_password(self, field):
        """Ensure new password is different from old password."""
        if field.data == self.oldpass.data:
            raise ValidationError(
                "New password must be different from current password."
            )


class UpdatePublicKeyForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "e.g. john_doe123", "autocomplete": "username"},
    )
    password = PasswordField(
        "Password",
        validators=password_validator(confirm_field="confirm"),
        render_kw={"autocomplete": "new-password"},
        description="Must contain uppercase, lowercase, digit, and special character (8-64 chars)",
    )
    confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(message="Please confirm your password.")],
        render_kw={"autocomplete": "new-password"},
    )
    public_key = FileField(
        "Public Key (PEM format)",
        validators=[
            FileRequired(message="Public key file is required."),
            FileAllowed(["pem", "key"], "Only .pem or .key files allowed."),
        ],
    )
    submit = SubmitField("Update Public Key")


class DeleteAccountForm(FlaskForm):
    """Form for account deletion - requires authentication."""

    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "Username", "autocomplete": "username"},
    )
    password = PasswordField(
        "Password",
        validators=password_validator(),
        render_kw={"autocomplete": "current-password"},
    )
    confirm = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
        render_kw={
            "placeholder": "Confirm your password",
            "autocomplete": "current-password",
        },
    )
    submit = SubmitField("Delete Account")


class GetPublicKeyForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "Enter username to get public key"},
    )
    submit = SubmitField("Get Public Key")


class ChatsForm(FlaskForm):
    username = StringField(
        "Username",
        validators=username_validator(),
        render_kw={"placeholder": "Username"},
    )
    submit = SubmitField("View Chats")


class SendFile(FlaskForm):
    recipient = StringField(
        "Recipient",
        validators=username_validator(),
        render_kw={"placeholder": "Recipient username"},
    )
    file = FileField(
        "File",
        validators=[
            FileRequired(message="Please select a file to send."),
        ],
    )
    submit = SubmitField("Send File")
