package com.tho.enterpriseai.user;

import org.springframework.data.jpa.repository.JpaRepository; // Chua cac cau lenh de tuong tac voi db
import java.util.Optional; // ép dev kiem tra xem trong hop co do hay khong truoc khi lay ra dung
import java.util.UUID;

public interface UserRepository extends JpaRepository<User, UUID>{
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
}
