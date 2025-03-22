// PriceScraper.js
const puppeteer = require('puppeteer');
const mysql = require('mysql2/promise');

async function setupBrowser() {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--disable-http2', '--no-sandbox', '--disable-setuid-sandbox'],
    });
    const page = await browser.newPage();
    await page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
        '(KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    );
    return { browser, page };
}

// asda
async function getAsdaPrice(url) {
    if (!url) return null;
    const { browser, page } = await setupBrowser();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('.pdp-main-details__price', { timeout: 30000 });
    const price = await page.evaluate(() => {
        const el = document.querySelector('.pdp-main-details__price');
        return el ? parseFloat(el.textContent.replace('now', '').replace('£', '').trim()) : null;
    });
    await browser.close();
    return price;
}

// sainsburys
async function getSainsburysPrice(url) {
    if (!url) return null;
    const { browser, page } = await setupBrowser();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('.pd__cost__retail-price', { timeout: 30000 });
    const price = await page.evaluate(() => {
        const el = document.querySelector('.pd__cost__retail-price');
        return el ? parseFloat(el.textContent.replace('£', '').trim()) : null;
    });
    await browser.close();
    return price;
}

// aldi
async function getAldiPrice(url) {
    if (!url) return null;
    const { browser, page } = await setupBrowser();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('span.product-price', { timeout: 30000 });
    const price = await page.evaluate(() => {
        const el = document.querySelector('span.product-price');
        return el ? parseFloat(el.textContent.replace('£', '').trim()) : null;
    });
    await browser.close();
    return price;
}


// upserter
async function upsertPrice(connection, productId, shopId, price) {
    const sql = `
    INSERT INTO ProductPrices (product_id, shop_id, price, rating, last_scraped_at)
    VALUES (?, ?, ?, 3.00, NOW())
    ON DUPLICATE KEY UPDATE 
      price = VALUES(price),
      rating = 3.00,
      last_scraped_at = NOW()
  `;
    const values = [productId, shopId, price];
    await connection.execute(sql, values);
}

// main
(async function scrapeAndStorePrices() {
    let connection;
    try {
        connection = await mysql.createConnection({
            host: 'brighton.reclaimhosting.com',
            user: 'tp558_Products',
            password: 'r}FxB.u8J^d2dr2',
            database: 'tp558_SupermarketPrices',
        });

        // get products
        const [products] = await connection.execute(`
      SELECT product_id, asda_link, aldi_link, sainsburys_link
      FROM Products
    `);

        for (const product of products) {
            const { product_id, asda_link, aldi_link, sainsburys_link } = product;

            let asdaPrice = null;
            let sainsPrice = null;
            let aldiPrice = null;

            // scrape Asda
            try {
                asdaPrice = await getAsdaPrice(asda_link);
            } catch (err) {
                console.error(
                    `Error scraping Asda (product_id=${product_id}, link=${asda_link}):`,
                    err
                );
            }

            // scrape sainsburys
            try {
                sainsPrice = await getSainsburysPrice(sainsburys_link);
            } catch (err) {
                console.error(
                    `Error scraping Sainsbury's (product_id=${product_id}, link=${sainsburys_link}):`,
                    err
                );
            }

            // scrape aldi
            try {
                aldiPrice = await getAldiPrice(aldi_link);
            } catch (err) {
                console.error(
                    `Error scraping Aldi (product_id=${product_id}, link=${aldi_link}):`,
                    err
                );
            }

            // upsert each price if available
            if (asdaPrice !== null) {
                await upsertPrice(connection, product_id, 1, asdaPrice);
            }
            if (sainsPrice !== null) {
                await upsertPrice(connection, product_id, 3, sainsPrice);
            }
            if (aldiPrice !== null) {
                await upsertPrice(connection, product_id, 2, aldiPrice);
            }
        }

        console.log('Scraping Complete');
    } catch (err) {
        console.error('Error Scraping:', err);
    } finally {
        if (connection) {
            await connection.end(); // close the database connection
        }
    }
})();
