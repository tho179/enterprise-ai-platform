package com.tho.enterpriseai.user;

import com.tho.enterpriseai.config.SecurityConfig;
import com.tho.enterpriseai.user.dto.CreateUserRequest;
import com.tho.enterpriseai.user.dto.UserResponse;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder){
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    // Get list users
    public List<UserResponse> getAllUsers(){
        return userRepository.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    // Create User
    public UserResponse createUser(CreateUserRequest request){
        // 1. Check email already exists
        if(userRepository.existsByEmail(request.getEmail())){
            throw new RuntimeException("Email already exists!");
        }

        // 2. Request DTO -> entity
        User user = User.builder()
                .fullName(request.getFullName())
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .role(request.getRole())
                .createdAt(LocalDateTime.now())
                .build();
        // 3. Save db
        User savedUser = userRepository.save(user);
        // 4. Entity -> Response DTO
        return toResponse(savedUser);
    }

    // User Entity -> User Response DTO
    private UserResponse toResponse(User user){
        return new UserResponse(
                user.getId(),
                user.getFullName(),
                user.getEmail(),
                user.getRole(),
                user.getCreatedAt()
        );
    }
}
