"use client"

import { useEffect, useMemo, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight, Building2, Calendar, Clock, MapPin, Stethoscope } from "lucide-react"

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

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

export default function PediatricSetup() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const statusParam = searchParams.get("status") // success | error | null

  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(true)

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

  const [calendarSynced, setCalendarSynced] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [oauthError, setOauthError] = useState<string | null>(null)

  const days = useMemo(
    () => [
      { day: "Lunes", start: "mondayStart", end: "mondayEnd" },
      { day: "Martes", start: "tuesdayStart", end: "tuesdayEnd" },
      { day: "Miércoles", start: "wednesdayStart", end: "wednesdayEnd" },
      { day: "Jueves", start: "thursdayStart", end: "thursdayEnd" },
      { day: "Viernes", start: "fridayStart", end: "fridayEnd" },
      { day: "Sábado", start: "saturdayStart", end: "saturdayEnd" },
      { day: "Domingo", start: "sundayStart", end: "sundayEnd" },
    ],
    []
  )

  const verifyStatus = async () => {
    setLoading(true)
    setOauthError(null)

    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/status`, {
        credentials: "include",
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      const data = await response.json()

      if (data.connected) {
        setCalendarSynced(true)
        setUserEmail(data.email ?? null)
      } else {
        setCalendarSynced(false)
        setUserEmail(null)
      }
    } catch (e) {
      console.error("El backend Python no está disponible o falló /api/auth/status", e)
      setCalendarSynced(false)
      setUserEmail(null)
    } finally {
      setLoading(false)
    }
  }

  // 1) Al montar: chequeo estado
  useEffect(() => {
    verifyStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 2) Si volvemos desde Google con ?status=success|error:
  //    - refrescamos status
  //    - limpiamos el query param para que no quede pegado
  useEffect(() => {
    if (!statusParam) return

    if (statusParam === "error") {
      setOauthError("No se pudo conectar con Google. Probá de nuevo.")
    }

    ;(async () => {
      await verifyStatus()
      // limpiar query param
      router.replace("/", { scroll: false })
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusParam])

  const handleNext = () => {
    if (step === 0) {
      setStep(1)
    } else if (step === 1 && clinicInfo.name && clinicInfo.address) {
      setStep(2)
    }
  }

  const handleBack = () => {
    if (step === 2) {
      setStep(1)
    } else if (step === 1) {
      setStep(0)
    }
  }

  // OAuth real (backend)
  const startGoogleOAuth = async () => {
    setOauthError(null)
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/google`, {
        credentials: "include",
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      const data = await response.json()
      if (data.url) window.location.href = data.url
      else throw new Error("No vino url en /api/auth/google")
    } catch (e) {
      console.error("Error: Python no responde /api/auth/google", e)
      setOauthError("Error: el servidor no respondió. ¿Está corriendo FastAPI en :8000?")
    }
  }

  // Por ahora “Crear nuevo calendario” también usa OAuth.
  // (Crear realmente un calendar nuevo = endpoint futuro)
  const handleCreateCalendar = async () => {
    await startGoogleOAuth()
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
          <p className="text-muted-foreground text-lg">Paso {step + 1} de 3</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex gap-2">
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 0 ? "bg-pediatric-primary" : "bg-muted"}`} />
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 1 ? "bg-pediatric-primary" : "bg-muted"}`} />
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 2 ? "bg-pediatric-primary" : "bg-muted"}`} />
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-center py-10 text-muted-foreground">
            Consultando al servidor…
          </div>
        )}

        {/* Step 0: Google Calendar Sync */}
        {!loading && step === 0 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Calendar className="w-6 h-6 text-pediatric-primary" />
                Sincronizar Calendario
              </CardTitle>
              <CardDescription>
                Conecta tu calendario de Google para gestionar las citas de tu consultorio
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="bg-pediatric-light/30 border border-pediatric-primary/20 rounded-lg p-6 space-y-4">
                <div className="flex items-start gap-3">
                  <Calendar className="w-5 h-5 text-pediatric-primary mt-0.5 flex-shrink-0" />
                  <div>
                    <h3 className="font-medium text-base mb-1">¿Por qué sincronizar?</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      Al conectar tu calendario de Google, podrás gestionar todas tus citas desde un solo lugar, recibir
                      recordatorios automáticos y mantener tu agenda siempre actualizada.
                    </p>
                  </div>
                </div>
              </div>

              {oauthError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-900">
                  {oauthError}
                </div>
              )}

              {calendarSynced && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-1">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <p className="text-sm font-medium text-green-900">Calendario conectado correctamente</p>
                  </div>
                  {userEmail && (
                    <p className="text-xs text-green-900/70">Cuenta: {userEmail}</p>
                  )}
                </div>
              )}

              <div className="space-y-3">
                <Button
                  onClick={startGoogleOAuth}
                  className="w-full h-12 text-base bg-white hover:bg-gray-50 text-gray-900 border border-gray-300"
                  size="lg"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
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
                  Sincronizar con Google Calendar
                </Button>

                <Button
                  onClick={handleCreateCalendar}
                  variant="outline"
                  className="w-full h-12 text-base bg-transparent"
                  size="lg"
                >
                  Crear Nuevo Calendario en Google
                </Button>
              </div>

              <div className="pt-4">
                <Button
                  onClick={handleNext}
                  disabled={!calendarSynced}
                  className="w-full h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                  size="lg"
                >
                  Continuar
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 1: Clinic Information */}
        {!loading && step === 1 && (
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

              <div className="flex gap-4">
                <Button onClick={handleBack} variant="outline" className="flex-1 h-12 text-base bg-transparent" size="lg">
                  Atrás
                </Button>
                <Button
                  onClick={handleNext}
                  disabled={!clinicInfo.name || !clinicInfo.address}
                  className="flex-1 h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                  size="lg"
                >
                  Continuar
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Office Hours */}
        {!loading && step === 2 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Clock className="w-6 h-6 text-pediatric-primary" />
                Horarios de Atención
              </CardTitle>
              <CardDescription>Define los horarios de atención para cada día de la semana</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {days.map((item) => (
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
                <Button onClick={handleBack} variant="outline" className="flex-1 h-12 text-base bg-transparent" size="lg">
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
