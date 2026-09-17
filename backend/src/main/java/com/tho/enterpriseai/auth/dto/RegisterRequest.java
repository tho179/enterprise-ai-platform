package com.tho.enterpriseai.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class RegisterRequest {

    @NotBlank(message = "Full Name is required!")
    private String fullName;

    @NotBlank(message = "Email is required!")
    @Email(message = "Email is invalid!")
    private String email;

    @NotBlank(message = "Password is required!")
    @Size(min = 6, message = "Password must contain at least 6 characters!")
    private String password;

}
