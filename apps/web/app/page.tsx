"use client"

import { useEffect, useMemo, useState } from "react"
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

type AuthStatus =
  | { connected: false }
  | { connected: true; email: string | null }

// ✅ ESTA ES TU PAGE
export default function Page() {
  const API_BASE = useMemo(() => "http://localhost:8000", [])

  const [step, setStep] = useState(0)
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

  const [loadingAuth, setLoadingAuth] = useState(true)
  const [calendarSynced, setCalendarSynced] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    const verifyStatus = async () => {
      setLoadingAuth(true)
      try {
        const res = await fetch(`${API_BASE}/api/auth/status`, {
          credentials: "include",
        })
        const data: AuthStatus = await res.json()

        if ("connected" in data && data.connected) {
          setCalendarSynced(true)
          setUserEmail(data.email ?? null)
        } else {
          setCalendarSynced(false)
          setUserEmail(null)
          setStep(0)
        }
      } catch (e) {
        console.error("Backend no disponible / error consultando status", e)
        setCalendarSynced(false)
        setUserEmail(null)
        setStep(0)
      } finally {
        setLoadingAuth(false)
      }
    }

    verifyStatus()
  }, [API_BASE])

  const handleGoogleSync = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/google`, {
        credentials: "include",
      })
      const data = await res.json()
      if (data?.url) window.location.href = data.url
      else alert("No se pudo obtener la URL de autenticación.")
    } catch (e) {
      console.error(e)
      alert("Error: Python no responde")
    }
  }

  const handleNext = () => {
    if (step === 0) setStep(1)
    else if (step === 1 && clinicInfo.name && clinicInfo.address) setStep(2)
  }

  const handleBack = () => {
    if (step === 2) setStep(1)
    else if (step === 1) setStep(0)
  }

  const handleSubmit = async () => {
    setSaveError(null)

    if (!userEmail) {
      setSaveError("No hay email conectado. Volvé a conectar Google Calendar.")
      setStep(0)
      return
    }
    if (!clinicInfo.name || !clinicInfo.address) {
      setSaveError("Completá nombre y dirección.")
      setStep(1)
      return
    }

    setSaving(true)
    try {
      const body = {
        email: userEmail,
        nombre: clinicInfo.name,
        direccion: clinicInfo.address,
        horarios: clinicInfo,
      }

      const res = await fetch(`${API_BASE}/api/rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Error creando sede (${res.status})`)
      }

      await res.json()
      setDone(true)
    } catch (e: any) {
      console.error(e)
      setSaveError(e?.message ?? "Error desconocido")
    } finally {
      setSaving(false)
    }
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
          <p className="text-muted-foreground text-lg">Paso {Math.min(step + 1, 3)} de 3</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex gap-2">
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 0 ? "bg-pediatric-primary" : "bg-muted"}`} />
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 1 ? "bg-pediatric-primary" : "bg-muted"}`} />
            <div className={`h-2 flex-1 rounded-full transition-colors ${step >= 2 ? "bg-pediatric-primary" : "bg-muted"}`} />
          </div>
        </div>

        {/* DONE */}
        {done && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="text-2xl">✅ Configuración completada</CardTitle>
              <CardDescription>Se creó el consultorio y se guardaron los horarios.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm font-medium text-green-900">Cuenta: {userEmail}</p>
                <p className="text-sm text-green-900">Consultorio: {clinicInfo.name}</p>
              </div>
              <Button className="w-full" onClick={() => { setDone(false); setStep(0) }}>
                Volver al inicio
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 0 */}
        {!done && step === 0 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Calendar className="w-6 h-6 text-pediatric-primary" />
                Sincronizar Calendario
              </CardTitle>
              <CardDescription>Conecta tu calendario de Google para gestionar las citas</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {loadingAuth ? (
                <div className="text-sm text-muted-foreground">Consultando al servidor...</div>
              ) : calendarSynced ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-sm font-medium text-green-900">Calendario conectado correctamente</p>
                  {userEmail && <p className="text-xs text-green-900/80">Cuenta: {userEmail}</p>}
                </div>
              ) : (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <p className="text-sm font-medium text-amber-900">Todavía no hay una cuenta conectada</p>
                </div>
              )}

              <Button
                onClick={handleGoogleSync}
                className="w-full h-12 text-base bg-white hover:bg-gray-50 text-gray-900 border border-gray-300"
                size="lg"
              >
                Conectar con Google Calendar
              </Button>

              <Button
                onClick={handleNext}
                disabled={!calendarSynced}
                className="w-full h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                size="lg"
              >
                Continuar
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 1 */}
        {!done && step === 1 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Building2 className="w-6 h-6 text-pediatric-primary" />
                Información del Consultorio
              </CardTitle>
              <CardDescription>Ingresa el nombre y la dirección</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-base font-medium">Nombre del Consultorio</Label>
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

        {/* Step 2 */}
        {!done && step === 2 && (
          <Card className="border-pediatric-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Clock className="w-6 h-6 text-pediatric-primary" />
                Horarios de Atención
              </CardTitle>
              <CardDescription>Define los horarios</CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {saveError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm font-medium text-red-900">Error: {saveError}</p>
                </div>
              )}

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
                <Button onClick={handleBack} variant="outline" className="flex-1 h-12 text-base bg-transparent" size="lg">
                  Atrás
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={saving}
                  className="flex-1 h-12 text-base bg-pediatric-primary hover:bg-pediatric-primary/90"
                  size="lg"
                >
                  {saving ? "Guardando..." : "Completar Configuración"}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
