"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { X, FileText, AlertCircle, Check, Edit, XCircle } from "lucide-react"

interface LeaseContractPageProps {
  /** Interrupt 데이터 */
  interruptData?: {
    aggregated_content?: string
    search_results_count?: number
    message?: string
    options?: {
      approve: string
      modify: string
      reject: string
    }
  }
  /** 승인 핸들러 */
  onApprove: () => void
  /** 수정 핸들러 */
  onModify: (modifications: string) => void
  /** 거부 핸들러 */
  onReject: () => void
  /** 페이지 닫기 핸들러 (X 버튼용) */
  onClose: () => void
}

/**
 * 임대차 계약서 페이지
 *
 * HITL (Human-in-the-Loop) 워크플로우에서 사용자 승인을 받기 위한 페이지
 *
 * 현재: 간단한 표시 + 수동 닫기만 구현
 * 추후: lease_contract_template_with_placeholders.docx 내용 표시 및 수정 기능 추가 예정
 */
export function LeaseContractPage({
  interruptData,
  onApprove,
  onModify,
  onReject,
  onClose
}: LeaseContractPageProps) {
  const [showModifyInput, setShowModifyInput] = useState(false)
  const [modifications, setModifications] = useState("")

  const handleApprove = () => {
    onApprove()
    onClose()
  }

  const handleModify = () => {
    if (!showModifyInput) {
      setShowModifyInput(true)
      return
    }

    if (modifications.trim()) {
      onModify(modifications)
      onClose()
    }
  }

  const handleReject = () => {
    onReject()
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      {/* 메인 컨테이너 */}
      <Card className="w-full max-w-4xl h-[90vh] flex flex-col bg-white">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-blue-600" />
            <div>
              <h2 className="text-2xl font-bold">임대차 계약서</h2>
              <p className="text-sm text-gray-500">Lease Contract</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-10 w-10"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* 알림 영역 */}
        {interruptData?.message && (
          <div className="mx-6 mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">
                {interruptData.message}
              </p>
              {interruptData.search_results_count !== undefined && (
                <p className="text-xs text-blue-700 mt-1">
                  검색 결과 {interruptData.search_results_count}개 기반으로 생성됨
                </p>
              )}
            </div>
          </div>
        )}

        {/* 메인 컨텐츠 영역 */}
        <div className="flex-1 overflow-auto p-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg h-full flex flex-col items-center justify-center text-gray-400">
            <FileText className="h-16 w-16 mb-4" />
            <p className="text-lg font-medium">계약서 편집 영역</p>
            <p className="text-sm mt-2">
              추후 lease_contract_template_with_placeholders.docx
            </p>
            <p className="text-sm">
              내용이 표시되고 수정할 수 있습니다
            </p>

            {/* 디버그: aggregated_content 표시 */}
            {interruptData?.aggregated_content && (
              <div className="mt-6 p-4 bg-gray-100 rounded max-w-2xl text-left">
                <p className="text-xs font-mono text-gray-600">
                  {interruptData.aggregated_content}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 푸터 - 수정 입력 영역 (조건부 표시) */}
        {showModifyInput && (
          <div className="p-6 border-t bg-amber-50">
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">
                수정 요청 사항을 입력하세요
              </label>
              <Textarea
                value={modifications}
                onChange={(e) => setModifications(e.target.value)}
                placeholder="예: 임대료를 월 100만원으로 조정해주세요..."
                className="min-h-[100px] resize-none"
              />
            </div>
          </div>
        )}

        {/* 푸터 - 액션 버튼 */}
        <div className="p-6 border-t bg-gray-50">
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm text-gray-500">
              {interruptData?.message || "내용을 검토하고 작업을 선택하세요"}
            </div>
            <div className="flex gap-3">
              <Button
                onClick={handleReject}
                variant="outline"
                size="lg"
                className="px-6 text-red-600 border-red-300 hover:bg-red-50"
              >
                <XCircle className="h-4 w-4 mr-2" />
                거부
              </Button>
              <Button
                onClick={handleModify}
                variant="outline"
                size="lg"
                className="px-6 text-amber-600 border-amber-300 hover:bg-amber-50"
              >
                <Edit className="h-4 w-4 mr-2" />
                {showModifyInput ? "수정 제출" : "수정"}
              </Button>
              <Button
                onClick={handleApprove}
                size="lg"
                className="px-6 bg-blue-600 hover:bg-blue-700"
              >
                <Check className="h-4 w-4 mr-2" />
                승인
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
