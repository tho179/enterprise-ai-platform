package com.tho.enterpriseai.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.UUID;

@Getter
@AllArgsConstructor
public class AuthResponse {
    private UUID id;
    private String fullName;
    private String email;
    private String role;
    private String accessToken;
}
