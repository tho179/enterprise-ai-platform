package com.tho.enterpriseai.security;

import com.tho.enterpriseai.user.User;
import com.tho.enterpriseai.user.UserRepository;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.security.SignatureException;
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

        // 1. Extract the Authorization header
        String authHeader = request.getHeader("Authorization");

        // 2. No Bearer token present — pass through and let Spring Security handle authorization
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        // 3. Strip the "Bearer " prefix to get the raw JWT
        String token = authHeader.substring(7);

        try {
            // 4. Extract email claim from JWT
            String email = jwtService.extractEmail(token);

            // 5. Load the user from the database
            User user = userRepository.findByEmail(email).orElse(null);

            // 6. Validate JWT signature, expiry, and user existence
            if (user == null || !jwtService.isTokenValid(token, user.getEmail())) {
                writeUnauthorized(response);
                return;
            }

            // 7. Build a granted authority with the ROLE_ prefix required by Spring Security hasRole()
            SimpleGrantedAuthority authority = new SimpleGrantedAuthority("ROLE_" + user.getRole());

            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(user.getEmail(), null, List.of(authority));

            SecurityContextHolder.getContext().setAuthentication(authentication);

        } catch (ExpiredJwtException | SignatureException | MalformedJwtException e) {
            // Token is invalid or expired — return 401 immediately
            writeUnauthorized(response);
            return;
        } catch (Exception e) {
            // Any other unexpected error — return 500
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            return;
        }

        // 8. Token is valid — continue the filter chain
        filterChain.doFilter(request, response);
    }

    private void writeUnauthorized(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        response.getWriter().write("{\"status\":401,\"error\":\"Unauthorized\",\"message\":\"Invalid or expired token\"}");
    }
}
