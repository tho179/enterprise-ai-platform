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

        // 1. Lay Authorization header
        String authHeader = request.getHeader("Authorization");

        // 2. Khong co Bearer Token -> cho request di tiep -> Spring security xu ly tiep
        if(authHeader == null || !authHeader.startsWith("Bearer ")){
            filterChain.doFilter(request, response);
            return;
        }

        // 3. Bo Bearer -> lay JWT
        String token = authHeader.substring(7);

        // Add try-catch de xu ly khi token het han thi hien thi loi de hieu
        try{
            // 4. Lay email tu JWT
            String email = jwtService.extractEmail(token);

            // 5. Tim User
            User user = userRepository.findByEmail(email).orElse(null);

            // 6. Validate JWT
            if(user == null || !jwtService.isTokenValid(token, user.getEmail())){
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.setCharacterEncoding("UTF-8");
                response.getWriter().write(
                        """
                                {
                                "status": 401,
                                "error": "Unauthorized",
                                "message": "Invalid or expired token"
                                }
                           """
                );
                return;
            }

            SimpleGrantedAuthority authority = new SimpleGrantedAuthority("ROLE_" + user.getRole());

            UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(user.getEmail(), null, List.of(authority));

            SecurityContextHolder
                    .getContext()
                    .setAuthentication(authentication);

        } catch (ExpiredJwtException | SignatureException | MalformedJwtException e) {

            // Chi bat nhung loi do token khong hop le hoac het han

            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);

            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            response.getWriter().write(
                    """
                        {
                         "status": 401,
                         "error": "Unauthorized",
                         "message": "Invalid or expired token"
                        }
                       """
            );
            return;
        } catch (Exception e) {
            // Cac loi khac nem 500
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            return;
        }

        // 10. Cho request đi tiếp
        filterChain.doFilter(request, response);
    }
}
