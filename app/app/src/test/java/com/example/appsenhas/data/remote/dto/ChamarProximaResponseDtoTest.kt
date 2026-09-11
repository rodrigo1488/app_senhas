package com.example.appsenhas.data.remote.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChamarProximaResponseDtoTest {
    @Test
    fun `decodifica payload legado e infere chamada pela senha`() {
        val response = Json.decodeFromString<ChamarProximaResponseDto>(
            """
            {
              "senha": {"id": 7, "senha": "N1007", "tipo": "normal"},
              "tipo_chamado": "normal",
              "alerta_preferenciais": false
            }
            """.trimIndent(),
        )

        assertTrue(response.chamada_realizada)
        assertEquals("N1007", response.senha?.senha)
        assertNull(response.mensagem)
        assertNull(response.session_token)
    }

    @Test
    fun `decodifica payload atual com senha e token de sessao`() {
        val response = Json.decodeFromString<ChamarProximaResponseDto>(
            """
            {
              "senha": {"id": 7, "senha": "N1007", "tipo": "normal"},
              "chamada_realizada": true,
              "mensagem": "Senha N1007 chamada com sucesso.",
              "tipo_chamado": "normal",
              "alerta_preferenciais": false,
              "session_token": "novo-token"
            }
            """.trimIndent(),
        )

        assertTrue(response.chamada_realizada)
        assertEquals("N1007", response.senha?.senha)
        assertEquals("novo-token", response.session_token)
    }

    @Test
    fun `decodifica fila vazia sem mascarar senha ausente`() {
        val response = Json.decodeFromString<ChamarProximaResponseDto>(
            """
            {
              "senha": null,
              "chamada_realizada": false,
              "mensagem": "Atendimento finalizado. Não há senhas pendentes.",
              "tipo_chamado": null,
              "alerta_preferenciais": false,
              "session_token": "novo-token"
            }
            """.trimIndent(),
        )

        assertFalse(response.chamada_realizada)
        assertNull(response.senha)
        assertNull(response.tipo_chamado)
    }
}
