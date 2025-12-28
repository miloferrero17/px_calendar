"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight, Building2, Clock, MapPin, Stethoscope } from "lucide-react"

type ClinicInfo = {
  name: string
  address: string
  mondayStart: string
  mondayEnd: string
  tuesdayStart: string
  tuesdayEnd: string
  wednesdayStart: string
  wednesdayEnd: string
  thursdayStart: string
  thursdayEnd: string
  fridayStart: string
  fridayEnd: string
  saturdayStart: string
  saturdayEnd: string
  sundayStart: string
  sundayEnd: string
}

export default function PediatricSetup() {
  const [step, setStep] = useState(1)
  const [clinicInfo, setClinicInfo] = useState<ClinicInfo>({
    name: "",
    address: "",
    mondayStart: "",
    mondayEnd: "",
    tuesdayStart: "",
    tuesdayEnd: "",
    wednesdayStart: "",
    wednesdayEnd: "",
    thursdayStart: "",
    thursdayEnd: "",
    fridayStart: "",
    fridayEnd: "",
    saturdayStart: "",
    saturdayEnd: "",
    sundayStart: "",
    sundayEnd: "",
  })

  const handleNext = () => {
    if (step === 1 && clinicInfo.name && clinicInfo.address) {
      setStep(2)
    }
  }

  const handleBack = () => {
    setStep(1)
  }

  const handleSubmit = () => {
    console.log("Clinic information:", clinicInfo)
    alert("¡Configuración completada! Revisa la consola para ver los datos.")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-pediatric-light via-background to-pediatric-accent/10 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-pediatric-primary mb-4">
            <Stethoscope className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">
            Configuración de Consultorio Pediátrico
          </h1>
          <p className="text-muted-foreground text-lg">Paso {step} de 2</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex gap-2">
            <div
              className={`h-2 flex-1 rounded-full transition-colors ${step >= 1 ? "bg-pediatric-primary" : "bg-muted"}`}
            />
            <div
              className={`h-2 flex-1 rounded-full transition-colors ${step >= 2 ? "bg-pediatric-primary" : "bg-muted"}`}
            />
          </div>
        </div>

        {/* Step 1: Clinic Information */}
        {step === 1 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Building2 className="w-6 h-6 text-pediatric-primary" />
                Información del Consultorio
              </CardTitle>
              <CardDescription>Ingresa el nombre y la dirección de tu consultorio pediátrico</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-base font-medium">
                  Nombre del Consultorio
                </Label>
                <Input
                  id="name"
                  placeholder="Ej: Consultorio Pediátrico Dr. García"
                  value={clinicInfo.name}
                  onChange={(e) => setClinicInfo({ ...clinicInfo, name: e.target.value })}
                  className="h-12 text-base"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address" className="text-base font-medium flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-pediatric-primary" />
                  Dirección
                </Label>
                <Input
                  id="address"
                  placeholder="Ej: Av. Principal 123, Ciudad"
                  value={clinicInfo.address}
                  onChange={(e) => setClinicInfo({ ...clinicInfo, address: e.target.value })}
                  className="h-12 text-base"
                />
              </div>

              <Button
                onClick={handleNext}
                disabled={!clinicInfo.name || !clinicInfo.address}
                className="w-full h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                size="lg"
              >
                Continuar
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Office Hours */}
        {step === 2 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Clock className="w-6 h-6 text-pediatric-primary" />
                Horarios de Atención
              </CardTitle>
              <CardDescription>Define los horarios de atención para cada día de la semana</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { day: "Lunes", start: "mondayStart", end: "mondayEnd" },
                { day: "Martes", start: "tuesdayStart", end: "tuesdayEnd" },
                { day: "Miércoles", start: "wednesdayStart", end: "wednesdayEnd" },
                { day: "Jueves", start: "thursdayStart", end: "thursdayEnd" },
                { day: "Viernes", start: "fridayStart", end: "fridayEnd" },
                { day: "Sábado", start: "saturdayStart", end: "saturdayEnd" },
                { day: "Domingo", start: "sundayStart", end: "sundayEnd" },
              ].map((item) => (
                <div
                  key={item.day}
                  className="grid grid-cols-1 md:grid-cols-[120px_1fr_1fr] gap-4 items-center p-4 rounded-lg bg-muted/30"
                >
                  <Label className="font-medium text-base">{item.day}</Label>
                  <div className="space-y-1">
                    <Label htmlFor={`${item.start}`} className="text-sm text-muted-foreground">
                      Hora de inicio
                    </Label>
                    <Input
                      id={item.start}
                      type="time"
                      value={clinicInfo[item.start as keyof ClinicInfo] as string}
                      onChange={(e) => setClinicInfo({ ...clinicInfo, [item.start]: e.target.value })}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={`${item.end}`} className="text-sm text-muted-foreground">
                      Hora de cierre
                    </Label>
                    <Input
                      id={item.end}
                      type="time"
                      value={clinicInfo[item.end as keyof ClinicInfo] as string}
                      onChange={(e) => setClinicInfo({ ...clinicInfo, [item.end]: e.target.value })}
                      className="h-10"
                    />
                  </div>
                </div>
              ))}

              <div className="flex gap-4 pt-4">
                <Button
                  onClick={handleBack}
                  variant="outline"
                  className="flex-1 h-12 text-base bg-transparent"
                  size="lg"
                >
                  Atrás
                </Button>
                <Button
                  onClick={handleSubmit}
                  className="flex-1 h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                  size="lg"
                >
                  Completar Configuración
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
