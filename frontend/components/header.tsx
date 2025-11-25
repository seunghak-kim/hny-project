"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { LoginModal } from "@/components/login-modal"
import { Map, FileText, Users, Calculator, User } from "lucide-react"
import type { PageType } from "@/app/page"

interface HeaderProps {
  currentPage?: PageType
  onPageChange?: (page: PageType) => void
}

export function Header({ currentPage, onPageChange }: HeaderProps) {
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [consultationPreparing, setConsultationPreparing] = useState(false)

  return (
    <>
      <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-border z-50">
        <div className="h-full max-w-full px-6 flex items-center justify-between">
          {/* Left Side - Logo & Navigation */}
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-primary cursor-pointer" onClick={() => onPageChange?.("chat")}>도와줘 홈즈냥즈</h1>
            </div>

            {/* Navigation Menu */}
            {onPageChange && (
              <nav className="flex items-center gap-2">
                <Button
                  variant={currentPage === "map" ? "default" : "ghost"}
                  onClick={() => onPageChange("map")}
                  className="gap-2"
                  size="sm"
                >
                  <Map className="h-4 w-4" />
                  지도 검색
                </Button>

                <Button
                  variant={currentPage === "lease_contract" ? "default" : "ghost"}
                  onClick={() => onPageChange("lease_contract")}
                  className="gap-2"
                  size="sm"
                >
                  <FileText className="h-4 w-4" />
                  계약서 생성
                </Button>

                <Button
                  variant={currentPage === "consultation" ? "default" : "ghost"}
                  onClick={() => onPageChange("consultation")}
                  className="gap-2"
                  size="sm"
                >
                  <Users className="h-4 w-4" />
                  매물 추천
                </Button>

                <Button
                  variant={currentPage === "tax_calculator" ? "default" : "ghost"}
                  onClick={() => setConsultationPreparing(true)}
                  className="gap-2"
                  size="sm"
                >
                  <Calculator className="h-4 w-4" />
                  세금 계산기
                </Button>
              </nav>
            )}
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

      {/* 준비중 알림 */}
      {consultationPreparing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" onClick={() => setConsultationPreparing(false)}>
          <div className="bg-white p-8 rounded-lg shadow-xl max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-xl font-bold mb-4 text-center">준비 중입니다</h2>
            <p className="text-muted-foreground text-center mb-6">
              해당 페이지는 현재 준비 중입니다.
              <br />
              빠른 시일 내에 서비스를 제공하겠습니다.
            </p>
            <Button onClick={() => setConsultationPreparing(false)} className="w-full">
              확인
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
