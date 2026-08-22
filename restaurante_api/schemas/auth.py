from pydantic import BaseModel, EmailStr, Field


class AuthSchema(BaseModel):
    access_token: str
    token_type: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChangeSchema(BaseModel):
    current_password: str = Field(..., min_length=3)

    new_password: str = Field(..., min_length=3)

    confirm_password: str = Field(..., min_length=3)

    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords not match')

        return self
