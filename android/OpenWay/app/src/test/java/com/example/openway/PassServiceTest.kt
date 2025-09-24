package com.example.openway

import android.content.Context
import com.example.openway.domain.PassService
import com.example.openway.domain.PassResult
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.junit.MockitoJUnitRunner

@RunWith(MockitoJUnitRunner::class)
class PassServiceTest {
    
    @Mock
    private lateinit var mockContext: Context
    
    @Test
    fun `PassService should parse PassResult correctly`() {
        // Тест парсинга JSON ответа от ESP
        val jsonResponse = """{"decision":"ALLOW","reason":"OK"}"""
        val result = PassResult.parse(jsonResponse)
        
        assert(result.decision == "ALLOW")
        assert(result.reason == "OK")
        assert(result.allowed == true)
    }
    
    @Test
    fun `PassService should handle DENY response`() {
        val jsonResponse = """{"decision":"DENY","reason":"TOKEN_INVALID"}"""
        val result = PassResult.parse(jsonResponse)
        
        assert(result.decision == "DENY")
        assert(result.reason == "TOKEN_INVALID")
        assert(result.allowed == false)
    }
    
    @Test
    fun `PassService should handle missing fields with defaults`() {
        val jsonResponse = """{}"""
        val result = PassResult.parse(jsonResponse)
        
        assert(result.decision == "DENY")
        assert(result.reason == "UNKNOWN")
        assert(result.allowed == false)
    }
}
