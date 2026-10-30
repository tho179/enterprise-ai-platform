package com.tho.enterpriseai.config;

import com.tho.enterpriseai.user.User;
import com.tho.enterpriseai.user.UserRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Creates the demo accounts used by the console on an empty database.
 * Safe to run on every start: existing emails are left untouched.
 */
@Component
public class DemoDataInitializer implements CommandLineRunner {

    private static final String DEMO_PASSWORD = "Demo@123";

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public DemoDataInitializer(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) {
        List<SeedUser> accounts = List.of(
                new SeedUser("Nguyễn Minh Quân", "admin@congty.vn", "ADMIN"),
                new SeedUser("Trần Thu Hà", "manager@congty.vn", "MANAGER"),
                new SeedUser("Nguyễn Văn A", "nva@congty.vn", "EMPLOYEE"),
                new SeedUser("Lê Hoàng B", "lhb@congty.vn", "EMPLOYEE"),
                new SeedUser("Phạm Đức Long", "it@congty.vn", "IT_SUPPORT"),
                new SeedUser("Vũ Thị C", "vtc@congty.vn", "EMPLOYEE")
        );

        for (SeedUser account : accounts) {
            if (userRepository.existsByEmail(account.email())) {
                continue;
            }
            userRepository.save(User.builder()
                    .fullName(account.fullName())
                    .email(account.email())
                    .password(passwordEncoder.encode(DEMO_PASSWORD))
                    .role(account.role())
                    .active(true)
                    .createdAt(LocalDateTime.now())
                    .build());
        }
    }

    private record SeedUser(String fullName, String email, String role) {
    }
}
