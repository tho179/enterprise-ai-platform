package com.tho.enterpriseai.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.util.Date;

@Service
public class JwtService {

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${jwt.expiration}")
    private long jwtExpiration;

    // Lay chuoi jwt sau do duc thanh 1 secretKey
    private SecretKey getSigningKey(){
        byte[] keyBytes = Decoders.BASE64.decode(jwtSecret);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    // Create Token
    public String generateToken(String email, String role){

        // Create started time and expiration
        Date now = new Date();
        Date expiration = new Date(now.getTime() + jwtExpiration);

        return Jwts.builder()
                .subject(email) // Chu so huu Token
                .claim("role", role) // Them thong tin role len Token
                .issuedAt(now) // Ngay cap Token
                .expiration(expiration) // Thoi han Token
                .signWith(getSigningKey()) // Lay secretKey them vao
                .compact(); // Gop tat ca lai thanh 1 String gom 3 thanh phan cach nhau boi dau "."
    }

    // Read JWT
    private Claims extractAllClaims(String token){
        return Jwts.parser()
                .verifyWith(getSigningKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    // Get email for Token
    public String extractEmail(String token){
        return extractAllClaims(token).getSubject();
    }

    // Get role for Token
    public String extractRole(String token){
        return extractAllClaims(token).get("role", String.class);
    }

    // Check Token Expiration
    private Date extractExpiration(String token){
        return extractAllClaims(token).getExpiration();
    }
    private boolean isTokenExpired(String token){
        return extractExpiration(token).before(new Date());
    }

    // Validate Token
    public boolean isTokenValid(String token, String email){
        String tokenEmail = extractEmail(token);
        return tokenEmail.equals(email) && !isTokenExpired(token);
        // Kiem tra token email trung voi email khong va thoi han cua token con khong
    }
}
