package com.tho.enterpriseai.security;

import com.tho.enterpriseai.user.User;
import com.tho.enterpriseai.user.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

/**
 * Utility component to retrieve the currently authenticated user's information
 * from the Spring Security context.
 */
@Component
public class CurrentUser {

    private final UserRepository userRepository;

    public CurrentUser(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Returns the email (username) of the currently authenticated user.
     *
     * @throws ResponseStatusException 401 if no authenticated user is found
     */
    public String email() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Vui lòng đăng nhập.");
        }
        return authentication.getName();
    }

    /**
     * Returns the full name of the currently authenticated user,
     * falling back to email if the user record is not found.
     */
    public String fullName() {
        String email = email();
        return userRepository.findByEmail(email)
                .map(User::getFullName)
                .orElse(email);
    }
}
