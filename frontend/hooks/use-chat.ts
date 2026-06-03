"use client"

import { useState, useCallback, useEffect } from 'react'
import { Message, Conversation, AgentType, SentimentType } from '@/lib/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://cloudwalk-agent-swarm-production.up.railway.app'

function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

function generateThreadId(): string {
  return `thread_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
}

function mapAgentType(agentUsed: string): AgentType {
  if (agentUsed.includes('knowledge')) return 'knowledge'
  if (agentUsed.includes('support')) return 'support'
  if (agentUsed.includes('handoff')) return 'handoff'
  if (agentUsed.includes('guardrail')) return 'guardrail'
  return 'knowledge'
}

function mapSentiment(sentiment?: string, escalated?: boolean): SentimentType | undefined {
  if (!escalated) return undefined
  if (sentiment === 'distressed') return 'critical'
  if (sentiment === 'urgent') return 'urgent'
  return undefined
}

export function useChat() {
  const [userId] = useState(() => 'client789')
  const [conversation, setConversation] = useState<Conversation>({
    threadId: '',
    messages: [],
    isLoading: false
  })

  useEffect(() => {
    setConversation(prev => ({
      ...prev,
      threadId: generateThreadId()
    }))
  }, [])

  const sendMessage = useCallback(async (content: string, overrideUserId?: string) => {
    const userMessage: Message = {
      id: generateId(),
      content,
      role: 'user',
      timestamp: new Date()
    }

    setConversation(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true
    }))

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          user_id: overrideUserId || userId,
          thread_id: conversation.threadId || undefined,
        }),
      })

      if (!response.ok) throw new Error(`API error: ${response.status}`)

      const data = await response.json()

      const assistantMessage: Message = {
        id: generateId(),
        content: data.response,
        role: 'assistant',
        timestamp: new Date(),
        agentType: mapAgentType(data.agent_used || ''),
        sentiment: mapSentiment(data.sentiment, data.escalated),
      }

      setConversation(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        isLoading: false,
        threadId: data.thread_id || prev.threadId,
      }))

    } catch (error) {
      const errorMessage: Message = {
        id: generateId(),
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.',
        role: 'assistant',
        timestamp: new Date(),
        agentType: 'knowledge',
      }

      setConversation(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
        isLoading: false,
      }))
    }
  }, [conversation.threadId, userId])

  const clearConversation = useCallback(() => {
    setConversation({
      threadId: generateThreadId(),
      messages: [],
      isLoading: false
    })
  }, [])

  return {
    conversation,
    sendMessage,
    clearConversation
  }
}