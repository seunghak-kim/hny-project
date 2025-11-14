"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { MessageCircle } from "lucide-react"

interface LoginModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function LoginModal({ open, onOpenChange }: LoginModalProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [name, setName] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    // TODO: 실제 로그인 API 호출
    setTimeout(() => {
      console.log("로그인:", { email, password })
      setIsLoading(false)
      onOpenChange(false)
    }, 1000)
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    // TODO: 실제 회원가입 API 호출
    setTimeout(() => {
      console.log("회원가입:", { name, email, password })
      setIsLoading(false)
      onOpenChange(false)
    }, 1000)
  }

  const handleSocialLogin = (provider: string) => {
    console.log(`${provider} 로그인`)
    // TODO: 소셜 로그인 처리
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] p-0 gap-0">
        <DialogHeader className="px-6 pt-6 pb-4">
          <DialogTitle className="text-center text-xl">
            지금 로그인하면<br />
            모든 정보를 확인할 수 있어요
          </DialogTitle>
        </DialogHeader>

        <div className="px-6 pb-6">
          <Tabs defaultValue="member" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="member">일반회원</TabsTrigger>
              <TabsTrigger value="realtor" className="relative">
                중개사회원
                <span className="absolute -top-2 -right-2 bg-teal-600 text-white text-xs font-semibold rounded-full w-5 h-5 flex items-center justify-center">
                  ?
                </span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="member">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">이메일</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="이메일을 입력하세요"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">비밀번호</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="비밀번호를 입력하세요"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full h-12 text-base font-semibold bg-yellow-400 hover:bg-yellow-500 text-gray-900"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                      로그인 중...
                    </div>
                  ) : (
                    <>
                      <MessageCircle className="mr-2 h-5 w-5" />
                      카카오로 1초 만에 시작
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="realtor">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="realtor-name">이름</Label>
                  <Input
                    id="realtor-name"
                    type="text"
                    placeholder="이름을 입력하세요"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="realtor-email">이메일</Label>
                  <Input
                    id="realtor-email"
                    type="email"
                    placeholder="이메일을 입력하세요"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="realtor-password">비밀번호</Label>
                  <Input
                    id="realtor-password"
                    type="password"
                    placeholder="비밀번호를 입력하세요"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full h-12 text-base font-semibold bg-yellow-400 hover:bg-yellow-500 text-gray-900"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                      처리 중...
                    </div>
                  ) : (
                    <>
                      <MessageCircle className="mr-2 h-5 w-5" />
                      카카오로 1초 만에 시작
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-background px-2 text-muted-foreground">또는</span>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-3">
            <Button
              type="button"
              variant="outline"
              className="h-14 rounded-full border-2"
              onClick={() => handleSocialLogin("Google")}
            >
              <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-6 h-6">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              </div>
            </Button>

            <Button
              type="button"
              variant="outline"
              className="h-14 rounded-full border-2"
              onClick={() => handleSocialLogin("Naver")}
            >
              <div className="w-8 h-8 rounded-full bg-[#03C75A] flex items-center justify-center">
                <span className="text-white font-bold text-xl">N</span>
              </div>
            </Button>

            <Button
              type="button"
              variant="outline"
              className="h-14 rounded-full border-2"
              onClick={() => handleSocialLogin("Apple")}
            >
              <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-5 h-5" fill="white">
                  <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                </svg>
              </div>
            </Button>

            <Button
              type="button"
              variant="outline"
              className="h-14 rounded-full border-2"
              onClick={() => handleSocialLogin("Email")}
            >
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <svg
                  viewBox="0 0 24 24"
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="M3 7l9 6 9-6" />
                </svg>
              </div>
            </Button>
          </div>

          <div className="mt-6 text-center text-xs text-muted-foreground space-x-2">
            <a href="#" className="hover:underline">
              이메일로 가입
            </a>
            <span>|</span>
            <a href="#" className="hover:underline">
              고객센터 문의
            </a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
