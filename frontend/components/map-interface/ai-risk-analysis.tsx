import React from 'react'
import { Shield, Lock, AlertTriangle, FileText, DollarSign, Building2, User } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function AIRiskAnalysis() {
    return (
        <div className="mt-6 space-y-6">
            {/* AI Safety Analysis Section */}
            <div className="border rounded-xl overflow-hidden shadow-sm bg-white">
                {/* Header */}
                <div className="bg-[#0d9488] px-4 py-3 flex items-center gap-2 text-white">
                    <Shield className="w-5 h-5" />
                    <h3 className="font-bold text-base">AI 매물 안전 분석</h3>
                </div>

                {/* Content Area with Blur Overlay */}
                <div className="relative p-5">
                    {/* Blurred Content */}
                    <div className="filter blur-sm select-none pointer-events-none opacity-60 space-y-6">
                        {/* Safety Score */}
                        <div className="flex flex-col items-center justify-center py-2">
                            <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-8 border-orange-400 border-t-gray-200 border-r-gray-200 rotate-[-45deg]">
                                <div className="rotate-[45deg] text-center">
                                    <span className="block text-3xl font-bold text-gray-800">72</span>
                                    <span className="text-xs text-gray-500">안전도</span>
                                </div>
                            </div>
                            <p className="mt-2 text-orange-500 font-bold">주의가 필요합니다</p>
                        </div>

                        {/* Risk Items */}
                        <div className="grid grid-cols-1 gap-3">
                            <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                                <div className="flex items-center gap-2 text-red-700">
                                    <AlertTriangle className="w-4 h-4" />
                                    <span className="font-medium text-sm">법적 리스크</span>
                                </div>
                                <span className="text-sm font-bold text-red-600">경매 이력 1건</span>
                            </div>

                            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                                <div className="flex items-center gap-2 text-gray-700">
                                    <DollarSign className="w-4 h-4" />
                                    <span className="font-medium text-sm">재무 리스크</span>
                                </div>
                                <span className="text-sm text-gray-500">건물주 대출 ██억</span>
                            </div>

                            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                                <div className="flex items-center gap-2 text-gray-700">
                                    <FileText className="w-4 h-4" />
                                    <span className="font-medium text-sm">서류 검증</span>
                                </div>
                                <span className="text-sm text-gray-500">등기부 ████</span>
                            </div>
                        </div>
                    </div>

                    {/* Login Overlay */}
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/40 backdrop-blur-[2px]">
                        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100 flex flex-col items-center text-center max-w-[280px]">
                            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
                                <Lock className="w-6 h-6 text-gray-600" />
                            </div>
                            <h4 className="font-bold text-gray-900 mb-1">로그인이 필요한 서비스입니다</h4>
                            <p className="text-xs text-gray-500 mb-4 leading-relaxed">
                                AI 기반 매물 안전 분석은<br />회원 전용 프리미엄 서비스입니다
                            </p>
                            <Button className="w-full bg-[#0d9488] hover:bg-[#0f766e] text-white h-9 text-sm">
                                로그인하고 전체 분석 보기
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Agent Connection Section */}
            <div className="border rounded-xl overflow-hidden shadow-sm bg-white">
                <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-gray-600" />
                        <h3 className="font-bold text-sm text-gray-800">전문 중개인 연결</h3>
                    </div>
                    <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">AD</span>
                </div>

                <div className="p-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                            <User className="w-6 h-6 text-gray-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                                <div className="h-4 w-16 bg-gray-200 rounded animate-pulse"></div>
                                <div className="h-3 w-8 bg-blue-100 rounded text-blue-600 text-[10px] flex items-center justify-center px-1">인증</div>
                            </div>
                            <div className="h-3 w-32 bg-gray-100 rounded animate-pulse"></div>
                        </div>
                        <Button variant="outline" size="sm" className="shrink-0 border-[#0d9488] text-[#0d9488] hover:bg-[#0d9488]/5">
                            상담 신청
                        </Button>
                    </div>
                    <p className="text-xs text-gray-400 mt-3 text-center">
                        로그인 후 담당 중개인의 상세 프로필을 확인할 수 있습니다.
                    </p>
                </div>
            </div>
        </div>
    )
}
