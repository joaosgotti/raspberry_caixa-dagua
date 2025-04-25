// src/App.jsx
import { useState, useEffect } from 'react';
import './App.css'; // Importe o arquivo CSS

// *** IMPORTAR BIBLIOTECA DE GRÁFICOS AQUI ***
// Exemplo (depois de instalar):
// import { Line } from 'react-chartjs-2';
// import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
// ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);


function App() {
  // Estados para os dados
  const [latestReading, setLatestReading] = useState(null);
  const [allReadings, setAllReadings] = useState([]); // Estado para todas as leituras (para o gráfico)

  // URLs dos seus endpoints
  const LATEST_READING_URL = 'https://projeto-caixa-dagua-api.onrender.com/leituras/ultima';
  // URL para todas as leituras (ajuste se precisar passar um parâmetro para 24h)
  const ALL_READINGS_URL = 'https://projeto-caixa-dagua-api.onrender.com/leituras'; // Assumindo que retorna uma lista, talvez grande

  // Função para buscar dados (agora busca última e todas as leituras)
  const fetchData = async () => {
    try {
      // Busca a última leitura
      const latestResponse = await fetch(LATEST_READING_URL);
      if (latestResponse.ok) {
        const latestData = await latestResponse.json();
        setLatestReading(latestData);
      } else {
         console.error(`Erro HTTP ao buscar última leitura! Status: ${latestResponse.status}`);
      }

      // Busca todas as leituras (para o gráfico)
      const allResponse = await fetch(ALL_READINGS_URL);
      if (allResponse.ok) {
         const allData = await allResponse.json();
         // *** AQUI: Você pode filtrar allData para as últimas 24h SE o backend retornar mais do que isso ***
         // Exemplo conceitual (requer lógica de data):
         // const last24HoursData = allData.filter(item => isWithinLast24Hours(item.created_on));
         // setAllReadings(last24HoursData);
         // Por enquanto, apenas armazena todos os dados recebidos:
         setAllReadings(allData);

      } else {
          console.error(`Erro HTTP ao buscar todas as leituras! Status: ${allResponse.status}`);
       }

    } catch (err) {
      console.error("Erro ao buscar dados:", err);
    }
  };

  // useEffect para buscar dados na montagem
  useEffect(() => {
    fetchData();
    // Opcional: buscar dados periodicamente (a cada 60 segundos, por exemplo)
    // const intervalId = setInterval(fetchData, 60000);
    // return () => clearInterval(intervalId); // Limpa o intervalo na desmontagem
  }, []);

  // Função para formatar a data/hora
   const formatTimestamp = (timestampString) => {
      if (!timestampString) return 'N/A';
      try {
          const date = new Date(timestampString);
          if (isNaN(date.getTime())) {
              throw new Error("Data inválida");
          }
          return date.toLocaleString();
      } catch (e) {
          console.error("Erro ao formatar timestamp:", timestampString, e);
          return timestampString;
      }
  };

  // *** PREPARAR DADOS PARA O GRÁFICO AQUI ***
  // Esta lógica dependerá da biblioteca de gráficos e do formato exato de allReadings
  // Exemplo conceitual para Chart.js:
  const chartData = {
      labels: allReadings.map(item => formatTimestamp(item.created_on)), // Eixos X (tempo)
      datasets: [
          {
              label: 'Distância (cm)',
              data: allReadings.map(item => item.distancia), // Eixo Y (valor)
              fill: false,
              backgroundColor: 'rgba(75,192,192,0.2)',
              borderColor: 'rgba(75,192,192,1)',
          },
      ],
  };

  // Opções do gráfico (exemplo Chart.js)
  const chartOptions = {
      responsive: true,
      plugins: {
          title: {
              display: true,
              text: 'Leituras das Últimas 24h', // Título do gráfico
              color: var('--primary-blue-light'), // Use a string for the CSS variable
          },
      },
      scales: {
          x: { // Eixo X (tempo)
            // type: 'time', // Pode ser necessário configurar tipo time scale dependendo da lib e formato data
            title: { display: true, text: 'Horário', color: var('--text-medium') },
            ticks: { color: var('--text-dark') },
            grid: { color: var('--border-color') },
          },
          y: { // Eixo Y (distância)
            title: { display: true, text: 'Distância (cm)', color: var('--text-medium') },
            ticks: { color: var('--text-dark') },
            grid: { color: var('--border-color') },
          }
      },
       maintainAspectRatio: false, // Permite controlar o tamanho pelo container
  };


  return (
    <div className="app-container"> {/* Container Flexbox principal */}

      {/* Título principal acima das colunas */}
      <h1>Leituras da Caixa D'água</h1>

      {/* Coluna 1: Última Leitura e Info Usuário (1/3) */}
      <div className="column part-1">
          <h2>Última Leitura</h2>
          <div className="reading-container">
              {latestReading ? (
                  <div>
                      <p><strong>ID:</strong> {latestReading.id || 'N/A'}</p>
                      {/* Ajuste a label para refletir que é distância, que geralmente é inversamente proporcional ao nível */}
                      <p><strong>Distância (Nível):</strong> {latestReading.distancia !== undefined ? `${latestReading.distancia} cm` : 'N/A'}</p>
                      <p><strong>Horário:</strong> {formatTimestamp(latestReading.created_on)}</p>
                  </div>
              ) : (
                  <p className="loading-text">Aguardando última leitura...</p>
              )}
          </div>

          {/* Informações do Usuário */}
          <div className="user-info">
              {/* Substitua 'sua-foto.jpg' pelo caminho da sua foto */}
              {/* Crie uma pasta 'public' na raiz do projeto e coloque a foto lá, ex: /public/minha-foto.jpg --> src="/minha-foto.jpg" */}
              <img src="/caminho-para-sua-foto.jpg" alt="Sua Foto" />
              <p>Seu Nome Completo</p> {/* Substitua pelo seu nome */}
              {/* Adicione outras informações se quiser */}
          </div>
      </div>

      {/* Coluna 2: Gráfico (2/3) */}
      <div className="column part-2">
          <h2>Gráfico das Últimas Leituras</h2>
          <div className="graph-container">
              {/* *** ÁREA DO GRÁFICO *** */}
              {allReadings.length > 0 ? (
                  // *** RENDERIZAR O COMPONENTE DO GRÁFICO AQUI ***
                  // Exemplo para react-chartjs-2:
                  // <Line data={chartData} options={chartOptions} />
                  <p>Placeholder do Gráfico - Implementação necessária</p> // Placeholder atual
              ) : (
                  <p className="loading-text">Aguardando dados para o gráfico...</p>
              )}
               {/* Mensagem explicando a necessidade da biblioteca */}
               {!allReadings.length && !latestReading && <p className="comment">O gráfico requer dados históricos e uma biblioteca de gráficos (ex: Chart.js + react-chartjs-2).</p>}
          </div>
      </div>

    </div>
  );
}

export default App;