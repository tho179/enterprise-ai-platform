package com.tho.enterpriseai.user.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@AllArgsConstructor

public class UserResponse {
    private UUID id;
    private String fullName;
    private String email;
    private String role;
    private LocalDateTime createdAt;
}
