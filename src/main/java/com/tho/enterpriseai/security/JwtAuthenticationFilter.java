package com.tho.enterpriseai.security;

import com.tho.enterpriseai.user.User;
import com.tho.enterpriseai.user.UserRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserRepository userRepository;

    public JwtAuthenticationFilter(JwtService jwtService, UserRepository userRepository) {
        this.jwtService = jwtService;
        this.userRepository = userRepository;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {

        // 1. Lay Authorization header
        String authHeader = request.getHeader("Authorization");

        // 2. Khong co Bearer Token -> cho request di tiep -> kiem tra nhung cai khac sau
        if(authHeader == null || !authHeader.startsWith("Bearer ")){
            filterChain.doFilter(request, response);
            return;
        }

        // 3. Bo Bearer -> lay JWT
        String token = authHeader.substring(7);

        // 4. Lay email tu JWT
        String email = jwtService.extractEmail(token);

        // 5. Tim User
        User user = userRepository.findByEmail(email).orElse(null);

        // 6. Validate JWT
        if(user != null && jwtService.isTokenValid(token, user.getEmail())){

            // 7. Lay quyen user
            SimpleGrantedAuthority authority = new SimpleGrantedAuthority("ROLE_" + user.getRole());

            // 8. Tao authentication
            UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(user.getEmail(), null, List.of(authority));

            // 9. Luu authentication
            SecurityContextHolder
                    .getContext()
                    .setAuthentication(authentication);

        }

        // 10. Cho request đi tiếp
        filterChain.doFilter(request, response);
    }
}
