'use client';

import { useState, useEffect } from 'react';

export default function ConfigPage() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const verifyStatus = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/auth/status', {
          credentials: 'include',
        });
        const data = await response.json();

        if (data.connected) {
          setUserEmail(data.email);
          setStep(2);
        } else {
          setStep(1);
        }
      } catch (error) {
        console.error("El backend Python no está disponible");
        setStep(1);
      } finally {
        setLoading(false);
      }
    };

    verifyStatus();
  }, []);

  const handleConnectGoogle = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/google', {
        credentials: 'include',
      });
      const data = await response.json();
      if (data.url) window.location.href = data.url;
    } catch (error) {
      alert("Error: Python no responde");
    }
  };

  if (loading) return <div className="text-center p-20">Consultando al Servidor Python...</div>;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-gray-100 space-y-6">
        <h1 className="text-2xl font-bold text-center">Configuración</h1>

        {step === 1 ? (
          <div className="space-y-4">
            <p className="text-gray-600 text-center">
              Para continuar, conectá tu Google Calendar a través de nuestro servidor.
            </p>
            <button
              onClick={handleConnectGoogle}
              className="w-full bg-blue-600 text-white font-medium py-3 rounded-xl hover:bg-blue-700 transition"
            >
              Conectar Google Calendar
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 text-green-700 rounded-xl text-center font-bold">
              ✓ Conexión verificada por Python
            </div>
            <p className="text-center text-gray-500">Cuenta: {userEmail}</p>
            <button
              onClick={() => setStep(3)}
              className="w-full bg-blue-600 text-white py-3 rounded-xl"
            >
              Configurar Sedes
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
