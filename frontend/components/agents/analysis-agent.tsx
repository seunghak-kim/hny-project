"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ContractAnalysis } from "./contract-analysis"
import { PropertyDocuments } from "./property-documents"

export function AnalysisAgent() {
  const [activeTab, setActiveTab] = useState("contract")

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h2 className="text-xl font-semibold text-foreground">분석 에이전트</h2>
        <p className="text-sm text-muted-foreground">계약서 및 부동산 서류를 분석하여 위험요소를 탐지합니다</p>
      </div>

      {/* Content */}
      <div className="flex-1 p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="contract">계약서 분석</TabsTrigger>
            <TabsTrigger value="documents">등기부등본/건축물대장</TabsTrigger>
          </TabsList>

          <TabsContent value="contract" className="mt-4 h-full">
            <ContractAnalysis />
          </TabsContent>

          <TabsContent value="documents" className="mt-4 h-full">
            <PropertyDocuments />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
