package com.tho.enterpriseai.auth;

import com.tho.enterpriseai.auth.dto.AuthResponse;
import com.tho.enterpriseai.auth.dto.LoginRequest;
import com.tho.enterpriseai.auth.dto.RegisterRequest;
import com.tho.enterpriseai.security.JwtService;
import com.tho.enterpriseai.user.User;
import com.tho.enterpriseai.user.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    // Register
    public AuthResponse register(RegisterRequest request){
        // 1. Check email
        if(userRepository.existsByEmail(request.getEmail())){
            throw new RuntimeException("Email already exists!");
        }
        // 2. Create map
        User user = User.builder()
                .fullName(request.getFullName())
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .role("EMPLOYEE")
                .createdAt(LocalDateTime.now())
                .build();
        // 3. Save db
        User savedUser = userRepository.save(user);
        // 3.1 Create Token after register
        String token = jwtService.generateToken(savedUser.getEmail(), savedUser.getRole());
        // 4. Return
        return toResponse(savedUser, token);

    }

    // Login
    public AuthResponse login(LoginRequest request){
        User user = userRepository.findByEmail(request.getEmail()).orElseThrow(() -> new RuntimeException("Invalid email!"));

        boolean passwordMatches = passwordEncoder.matches(
                request.getPassword(),
                user.getPassword()
        );
        if(!passwordMatches){
            throw new RuntimeException("Invalid password!");
        }
        String token = jwtService.generateToken(user.getEmail(), user.getRole());
        return toResponse(user, token);

    }

    private AuthResponse toResponse(User user, String token){
        return new AuthResponse(
                user.getId(),
                user.getFullName(),
                user.getEmail(),
                user.getRole(),
                token
        );
    }
}
