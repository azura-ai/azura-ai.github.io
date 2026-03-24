document.addEventListener('DOMContentLoaded', () => {
    // Dynamic Card Rendering
    // Dynamic Card Rendering
    async function renderDynamicContent() {
        const ROOT_PATH = window.ROOT_PATH || '';
        
        const blogGrid = document.querySelector('.blog-grid');
        const caseGrid = document.querySelector('.cases-grid');
        
        // Only fetch if grids are empty (Server environment)
        // Handle Load More for pre-baked cards or dynamic ones
        const loadMoreBtn = document.getElementById('load-more-blog');
        if (loadMoreBtn) {
            loadMoreBtn.onclick = async () => {
                try {
                    const response = await fetch(`${ROOT_PATH}content.json`);
                    const data = await response.json();
                    
                    const existingCount = blogGrid.querySelectorAll('.blog-card').length;
                    const nextBatch = data.blogs.slice(existingCount, existingCount + 6);
                    
                    const newCards = nextBatch.map((blog, i) => {
                        const imgUrl = blog.image ? (blog.image.startsWith('http') ? blog.image : ROOT_PATH + blog.image) : '';
                        return `
                        <div class="blog-card animate-in" style="animation-delay: ${i * 0.1}s">
                            <div class="blog-img" style="background: ${imgUrl ? `url('${imgUrl}') center/cover` : `linear-gradient(135deg, hsl(${260 + (existingCount+i) * 20}, 70%, 50%), hsl(${220 + (existingCount+i) * 20}, 70%, 40%))`};">
                                ${!imgUrl ? `<div class="img-overlay"></div>` : ''}
                            </div>
                            <div class="blog-content" style="padding: 3rem;">
                                <span class="blog-tag">Insight</span>
                                <h3>${blog.title}</h3>
                                <p>${blog.subtitle ? blog.subtitle.substring(0, 100) + '...' : ''}</p>
                                <a href="${ROOT_PATH}blog/${blog.id}/" class="read-more">Read Insight <i class="fas fa-arrow-right"></i></a>
                            </div>
                        </div>`;
                    }).join('');
                    
                    loadMoreBtn.parentElement.insertAdjacentHTML('beforebegin', newCards);
                    
                    if (existingCount + nextBatch.length >= data.blogs.length) {
                        loadMoreBtn.parentElement.remove();
                    }
                    
                    // Observe new elements
                    document.querySelectorAll('.blog-card.animate-in').forEach(el => {
                        if (typeof observer !== 'undefined') observer.observe(el);
                    });
                } catch (err) { console.error('Load more failed:', err); }
            };
        }
        
        // Render Cases if empty
        if (caseGrid && caseGrid.children.length === 0) {
            try {
                const response = await fetch(`${ROOT_PATH}content.json`);
                const data = await response.json();
                caseGrid.innerHTML = data.cases.map(study => `
                    <div class="case-card">
                        <div class="case-header">
                            <span class="case-badge">Impact Analysis</span>
                            <h3>${study.title}</h3>
                        </div>
                        <p>${study.subtitle}</p>
                        <a href="${ROOT_PATH}case/${study.id}/index.html" class="read-more">View Full Breakdown <i class="fas fa-arrow-right"></i></a>
                    </div>`).join('');
            } catch (err) {}
        }
        document.querySelectorAll('.blog-card, .case-card').forEach(el => {
            if (typeof observer !== 'undefined') observer.observe(el);
        });
    }
    renderDynamicContent();
    // Chatbot Toggle
    const trigger = document.getElementById('chatbot-trigger');
    const widget = document.getElementById('chatbot-widget');
    const closeBtn = document.getElementById('close-chat');

    trigger.addEventListener('click', () => {
        widget.classList.toggle('chatbot-closed');
    });

    closeBtn.addEventListener('click', () => {
        widget.classList.add('chatbot-closed');
    });

    // Chat Logic
    const sendBtn = document.getElementById('send-msg');
    const input = document.querySelector('.chat-input input');
    const messages = document.getElementById('chat-messages');

    const addMessage = (text, isBot = false) => {
        const msg = document.createElement('div');
        msg.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
        msg.textContent = text;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    };

    const handleSend = async () => {
        const text = input.value.trim();
        if (text) {
            addMessage(text);
            input.value = '';
            
            // Show loading bubble
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'message bot-message loading';
            loadingMsg.textContent = 'Typing...';
            messages.appendChild(loadingMsg);
            messages.scrollTop = messages.scrollHeight;

            try {
                // Call actual FastAPI backend on Railway
                const response = await fetch('https://nexus-intelgithubio-production.up.railway.app/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        patient_id: 'GUEST',
                        patient_name: 'Visitor',
                        message: text 
                    })
                });
                
                const data = await response.json();
                messages.removeChild(loadingMsg);
                addMessage(data.response, true);
            } catch (err) {
                messages.removeChild(loadingMsg);
                // Fallback to simulation if backend is not reachable
                setTimeout(() => {
                    const responses = [
                        "I'd be happy to help you with your AI project! I noticed you might be interested in our AI Audit.",
                        "Our expertise in OCR can definitely scale your operations globally.",
                        "We specialize in LangGraph for complex agentic workflows in the US and Europe.",
                        "Nexus delivers premium solutions in Python and Go for international clients.",
                        "Let's book a discovery call to discuss your regional RAG implementation."
                    ];
                    const rand = Math.floor(Math.random() * responses.length);
                    addMessage(responses[rand], true);
                }, 1000);
            }
        }
    };

    sendBtn.addEventListener('click', handleSend);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    // Scroll Animations
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.service-card, .tech-group, .blog-card, .case-card, .contact-container').forEach(el => {
        observer.observe(el);
    });

    // Form Submissions
    const contactForm = document.getElementById('contact-form');
    const newsletterForm = document.getElementById('newsletter-form');

    const handleFormSubmit = async (e, endpoint, successMsg) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        const originalText = btn.textContent;
        
        // Extract data
        const formData = {};
        const inputs = e.target.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            const label = input.previousElementSibling ? input.previousElementSibling.textContent.toLowerCase() : 'email';
            formData[label] = input.value;
        });

        btn.textContent = 'Sending...';
        btn.disabled = true;

        try {
            const response = await fetch(`https://nexus-intelgithubio-production.up.railway.app/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error('Backend unavailable');

            btn.textContent = 'Success!';
            btn.style.background = '#10b981';
            alert(successMsg);
            e.target.reset();
        } catch (err) {
            console.warn('Form submission fallback:', err);
            // Simulate success for demo purposes if backend is down
            setTimeout(() => {
                btn.textContent = 'Success (Demo)!';
                btn.style.background = '#3b82f6';
                alert(successMsg + ' (Simulation Mode)');
                e.target.reset();
            }, 1000);
        } finally {
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.disabled = false;
            }, 3000);
        }
    };

    if (contactForm) {
        contactForm.addEventListener('submit', (e) => handleFormSubmit(e, 'contact', 'Message sent successfully! We will get back to you soon.'));
    }

    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => handleFormSubmit(e, 'newsletter', 'Thanks for subscribing to our newsletter!'));
    }

    // ROI Calculator Logic
    const volInput = document.getElementById('doc-volume');
    const costInput = document.getElementById('unit-cost');
    const volVal = document.getElementById('vol-val');
    const costVal = document.getElementById('cost-val');
    const savingsTotal = document.getElementById('savings-total');

    if (volInput && costInput) {
        const calculateROI = () => {
            const vol = parseInt(volInput.value);
            const cost = parseFloat(costInput.value);
            
            volVal.textContent = vol.toLocaleString();
            costVal.textContent = cost.toFixed(2);
            
            // Assume 80% cost reduction with AI
            const manualAnnual = vol * cost * 12;
            const aiAnnual = manualAnnual * 0.2;
            const savings = manualAnnual - aiAnnual;
            
            savingsTotal.textContent = `$${Math.round(savings).toLocaleString()}`;
        };

        volInput.addEventListener('input', calculateROI);
        costInput.addEventListener('input', calculateROI);
        calculateROI(); // Initial calc
    }

    // Data Flow Particle System
    const initDataFlow = () => {
        const containers = document.querySelectorAll('.data-flow-viz');
        containers.forEach(container => {
            setInterval(() => {
                // Particle from source to core
                const p1 = document.createElement('div');
                p1.className = 'flow-particle';
                p1.style.top = (Math.random() * 60 + 20) + '%';
                p1.style.animation = `flow-left-to-center ${Math.random() * 1 + 1.5}s infinite linear`;
                container.appendChild(p1);
                setTimeout(() => p1.remove(), 2500);

                // Particle from core to destination
                setTimeout(() => {
                    const p2 = document.createElement('div');
                    p2.className = 'flow-particle';
                    p2.style.top = (Math.random() * 60 + 20) + '%';
                    p2.style.animation = `flow-center-to-right ${Math.random() * 1 + 1.5}s infinite linear`;
                    container.appendChild(p2);
                    setTimeout(() => p2.remove(), 2500);
                }, 1000);
            }, 800);
        });
    };

    initDataFlow();
    renderDynamicContent();
});

// Chatbot Toggle Logic
const chatbotWidget = document.getElementById('chatbot-widget');
const chatbotTrigger = document.getElementById('chatbot-trigger');
const closeChat = document.getElementById('close-chat');

if (chatbotTrigger && chatbotWidget) {
    chatbotTrigger.addEventListener('click', () => {
        chatbotWidget.classList.toggle('chatbot-open');
    });
}
if (closeChat && chatbotWidget) {
    closeChat.addEventListener('click', () => {
        chatbotWidget.classList.remove('chatbot-open');
    });
}

// Chatbot Message Helper
function appendMessage(role, text) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role === 'bot' ? 'bot-message' : 'user-message'}`;
    
    // RENDER MARKDOWN if it's the bot
    if (role === 'bot' && typeof marked !== 'undefined') {
        msgDiv.innerHTML = marked.parse(text);
    } else {
        msgDiv.innerText = text;
    }
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Form Submission (Lead Gen)
    const leadForm = document.getElementById('leadForm');
    if (leadForm) {
        leadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = leadForm.querySelector('button');
            const originalText = btn.innerText;
            btn.innerText = 'Analyzing Workflow...';
            
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const message = document.getElementById('message').value;

            try {
                const response = await fetch('https://nexus-intelgithubio-production.up.railway.app/contact', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, message })
                });

                if (!response.ok) throw new Error('API Error');
                
                btn.innerText = 'Analysis Sent. Check Email.';
                btn.style.background = '#10b981';
                leadForm.reset();
            } catch (err) {
                console.warn('Form Error:', err);
                btn.innerText = 'Error. Please try again.';
                btn.style.background = '#ef4444';
            } finally {
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.style.background = '';
                }, 3000);
            }
        });
    }

// Pagination Logic: Load More
function loadMore(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const hiddenCards = container.querySelectorAll('.hidden-card');
    const toShow = 6;
    
    for (let i = 0; i < Math.min(toShow, hiddenCards.length); i++) {
        hiddenCards[i].classList.remove('hidden-card');
        hiddenCards[i].style.opacity = '0';
        setTimeout(() => {
            hiddenCards[i].style.opacity = '1';
        }, 10);
    }
    
    // Hide button if no more hidden cards
    if (container.querySelectorAll('.hidden-card').length === 0) {
        const btn = document.querySelector(`button[onclick*="${containerId}"]`);
        if (btn && btn.parentElement.classList.contains('pagination-container')) {
            btn.parentElement.style.display = 'none';
        }
    }
}
