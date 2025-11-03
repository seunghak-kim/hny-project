"use client"

import { useState } from "react"
import Image from "next/image"
import { X } from "lucide-react"
import { ChatInterface } from "@/components/chat-interface"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function FloatingChatButton() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 group"
          aria-label="Open chat"
        >
          <div className="w-20 h-20 rounded-full overflow-hidden shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110">
            <Image
              src="/images/hover_chat.jpg"
              alt="Chat with Holmes Nyangz"
              width={80}
              height={80}
              className="object-cover"
              priority
            />
          </div>
        </button>
      )}

      {/* Chat Modal */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-[450px] h-[650px] shadow-2xl rounded-lg overflow-hidden">
          <Card className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-primary text-primary-foreground">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full overflow-hidden">
                  <Image
                    src="/images/hover_chat.jpg"
                    alt="Holmes Nyangz"
                    width={40}
                    height={40}
                    className="object-cover"
                  />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">도와줘 홈즈냥즈</h3>
                  <p className="text-xs opacity-90">AI 부동산 가디언</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsOpen(false)}
                className="text-primary-foreground hover:bg-primary-foreground/20"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Chat Interface */}
            <div className="flex-1 overflow-hidden">
              <ChatInterface onSplitView={() => {}} currentSessionId={null} />
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
