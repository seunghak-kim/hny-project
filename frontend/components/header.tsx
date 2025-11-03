"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { LoginModal } from "@/components/login-modal"
import { User } from "lucide-react"

export function Header() {
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  return (
    <>
      <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-border z-50">
        <div className="h-full max-w-full px-6 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-primary">도와줘 홈즈냥즈</h1>
          </div>

          {/* Right Side - Login Button */}
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" className="gap-2">
                  <User className="h-4 w-4" />
                  <span>마이페이지</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLoggedIn(false)}
                >
                  로그아웃
                </Button>
              </div>
            ) : (
              <Button
                variant="default"
                size="sm"
                className="bg-primary hover:bg-primary/90"
                onClick={() => setLoginModalOpen(true)}
              >
                로그인
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Spacer to prevent content from going under fixed header */}
      <div className="h-16" />

      <LoginModal open={loginModalOpen} onOpenChange={setLoginModalOpen} />
    </>
  )
}
