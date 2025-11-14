"use client"

import { cn } from "@/lib/utils"

interface ProgressBarProps {
  value: number              // 0-100
  max?: number              // 기본값 100
  size?: "sm" | "md" | "lg"
  variant?: "default" | "success" | "warning" | "error"
  showLabel?: boolean
  className?: string
}

/**
 * 재사용 가능한 진행률 바 컴포넌트
 */
export function ProgressBar({
  value,
  max = 100,
  size = "md",
  variant = "default",
  showLabel = false,
  className
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3"
  }

  const variantClasses = {
    default: "bg-primary",
    success: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500"
  }

  return (
    <div className={cn("w-full", className)}>
      <div
        className={cn(
          "relative w-full rounded-full bg-muted overflow-hidden",
          sizeClasses[size]
        )}
      >
        <div
          className={cn(
            "h-full transition-all duration-300 ease-in-out",
            variantClasses[variant]
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-xs text-muted-foreground text-right mt-1">
          {percentage.toFixed(0)}%
        </div>
      )}
    </div>
  )
}
