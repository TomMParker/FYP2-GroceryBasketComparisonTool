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

// asda rating
async function getAsdaRating(url) {
    if (!url) return null;
    const { browser, page } = await setupBrowser();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('.co-product__rating', { timeout: 30000 });
    const rating = await page.evaluate(() => {
        const el = document.querySelector('.co-product__rating');
        if (el) {
            const ariaLabel = el.getAttribute('aria-label');
            const match = ariaLabel.match(/(\d+\.\d+)/); // extract rating
            return match ? parseFloat(match[1]) : null;
        }
        return null;
    });
    await browser.close();
    return rating;
}

// sainsbury rating
async function getSainsburysRating(url) {
    if (!url) return null;
    const { browser, page } = await setupBrowser();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('.ds-c-rating__stars', { timeout: 30000 });
    const rating = await page.evaluate(() => {
        const el = document.querySelector('.ds-c-rating__stars');
        if (el) {
            const title = el.getAttribute('title');
            const match = title.match(/(\d+\.\d+)/);
            return match ? parseFloat(match[1]) : null;
        }
        return null;
    });
    await browser.close();
    return rating;
}

// upserter
async function upsertRating(connection, productId, shopId, rating) {
    const sql = `
        INSERT INTO ProductPrices (product_id, shop_id, rating, last_scraped_at)
        VALUES (?, ?, ?, NOW())
        ON DUPLICATE KEY UPDATE 
            rating = VALUES(rating),
            last_scraped_at = NOW()
    `;
    const values = [productId, shopId, rating];
    await connection.execute(sql, values);
}

// main
(async function scrapeAndUpdateRatings() {
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
            SELECT product_id, asda_link, sainsburys_link
            FROM Products
        `);

        for (const product of products) {
            const { product_id, asda_link, sainsburys_link } = product;

            let asdaRating = null;
            let sainsRating = null;

            // scrape Asda rating
            try {
                asdaRating = await getAsdaRating(asda_link);
            } catch (err) {
                console.error(
                    `Error scraping Asda rating (product_id=${product_id}, link=${asda_link}):`,
                    err
                );
            }

            // scrape sainsburys Rating
            try {
                sainsRating = await getSainsburysRating(sainsburys_link);
            } catch (err) {
                console.error(
                    `Error scraping Sainsbury's rating (product_id=${product_id}, link=${sainsburys_link}):`,
                    err
                );
            }

            // upsert each price if available
            if (asdaRating !== null) {
                await updateRating(connection, product_id, 1, asdaRating);
            }
            if (sainsRating !== null) {
                await updateRating(connection, product_id, 3, sainsRating);
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