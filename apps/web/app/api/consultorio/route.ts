// apps/web/app/api/consultorio/route.ts
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name, address, email } = body;

    // 1. Validar datos mínimos
    if (!name || !address || !email) {
      return NextResponse.json(
        { error: "Faltan datos obligatorios (nombre, dirección o email)" },
        { status: 400 }
      );
    }

    // 2. Llamada al backend de Python (Flask)
    // Usamos el endpoint que ya tienes configurado o uno nuevo que invoque alta_consultorio.py
    const backendUrl = "http://127.0.0.1:5000/api/alta-consultorio"; 
    
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email,
        nombre: name,
        direccion: address,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Error en el servidor de Python");
    }

    return NextResponse.json({ success: true, data });
  } catch (error: any) {
    console.error("Error en API Route:", error);
    return NextResponse.json(
      { error: error.message || "Error interno del servidor" },
      { status: 500 }
    );
  }
}