"use client"

import { useState } from "react"
import { ChatInterface } from "@/components/chat-interface"
import { MapInterface } from "@/components/map-interface"
import { AnalysisAgent } from "@/components/agents/analysis-agent"
import { VerificationAgent } from "@/components/agents/verification-agent"
import { ConsultationAgent } from "@/components/agents/consultation-agent"
import { LeaseContractPage } from "@/components/lease_contract/lease_contract_page"
import { CognitiveDashboard } from "@/components/dashboards/cognitive-dashboard"
import { ExecutionDashboard } from "@/components/dashboards/execution-dashboard"
import { Header } from "@/components/header"

export type PageType = "chat" | "map" | "lease_contract" | "analysis" | "verification" | "consultation" | "cognitive_dashboard" | "execution_dashboard" | "tax_calculator"

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageType>("map")

  const handlePageChange = (page: PageType) => {
    setCurrentPage(page)
  }

  const renderLeftContent = () => {
    switch (currentPage) {
      case "chat":
        return null // 채팅 페이지에서는 왼쪽에 아무것도 표시하지 않음
      case "map":
        return <MapInterface />
      case "lease_contract":
        return (
          <LeaseContractPage
            onApprove={() => console.log('Approved')}
            onModify={(modifications) => console.log('Modified:', modifications)}
            onReject={() => console.log('Rejected')}
            onClose={() => setCurrentPage("chat")}
            onClosePopup={() => setCurrentPage("chat")}
            isPopup={false}
          />
        )
      case "analysis":
        return <AnalysisAgent />
      case "verification":
        return <VerificationAgent />
      case "consultation":
        return <ConsultationAgent />
      case "cognitive_dashboard":
        return <CognitiveDashboard />
      case "execution_dashboard":
        return <ExecutionDashboard />
      default:
        return null
    }
  }

  const leftContent = renderLeftContent()
  const showSplitView = leftContent !== null

  return (
    <>
      <Header currentPage={currentPage} onPageChange={handlePageChange} />
      <div className="flex bg-background" style={{ height: 'calc(100vh - 64px)' }}>
        {/* 왼쪽: 에이전트 영역 (지도, 계약서, 매물추천 등) */}
        {showSplitView && (
          <div className="flex-1 border-r border-border overflow-auto">
            {leftContent}
          </div>
        )}

        {/* 오른쪽: 메인 챗봇 (항상 표시) */}
        <div className={showSplitView ? "flex-1" : "w-full"}>
          <ChatInterface />
        </div>
      </div>
    </>
  )
}
